/*
 * The MIT License (MIT)
 *
 * Copyright 2022 Vladimir Mikhailov <beykerykt@gmail.com>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
package ru.beykerykt.minecraft.lightapi.bukkit.internal.handler.craftbukkit.nms.v1_21_R3;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ThreadedLevelLightEngine;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.LightLayer;
import net.minecraft.world.level.block.state.BlockState;

import org.bukkit.Bukkit;
import org.bukkit.World;
import org.bukkit.craftbukkit.CraftWorld;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

import ca.spottedleaf.moonrise.patches.starlight.blockstate.StarlightAbstractBlockState;
import ca.spottedleaf.moonrise.patches.starlight.light.BlockStarLightEngine;
import ca.spottedleaf.moonrise.patches.starlight.light.SkyStarLightEngine;
import ca.spottedleaf.moonrise.patches.starlight.light.StarLightEngine;
import ca.spottedleaf.moonrise.patches.starlight.light.StarLightInterface;
import ca.spottedleaf.moonrise.patches.starlight.light.StarLightLightingProvider;
import ru.beykerykt.minecraft.lightapi.bukkit.internal.BukkitPlatformImpl;
import ru.beykerykt.minecraft.lightapi.common.api.ResultCode;
import ru.beykerykt.minecraft.lightapi.common.api.engine.LightFlag;
import ru.beykerykt.minecraft.lightapi.common.internal.engine.LightEngineType;
import ru.beykerykt.minecraft.lightapi.common.internal.utils.FlagUtils;

/**
 * Handler for Paper 1.21.4, where the vanilla light engine is replaced by Moonrise's built-in Starlight.
 * Starlight work is done on the main thread, so there is no light mailbox to pause as in older versions.
 */
public class StarlightNMSHandler extends VanillaNMSHandler {

    private static final int ALL_DIRECTIONS_BITSET = (1 << 6) - 1;
    private static final long FLAG_HAS_SIDED_TRANSPARENT_BLOCKS = Long.MIN_VALUE;

    private final Map<ChunkPos, Set<LightPos>> blockQueueMap = new ConcurrentHashMap<>();
    private final Map<ChunkPos, Set<LightPos>> skyQueueMap = new ConcurrentHashMap<>();

    // StarLightEngine
    private Method starEngine_setLightLevel;
    private Method starEngine_appendToIncreaseQueue;
    private Method starEngine_performLightIncrease;
    private Method starEngine_updateVisible;
    private Method starEngine_setupCaches;
    private Method starEngine_destroyCaches;
    private java.lang.reflect.Field starEngine_coordinateOffset;

    private StarLightInterface getStarInterface(ThreadedLevelLightEngine lightEngine) {
        return ((StarLightLightingProvider) lightEngine).starlight$getLightEngine();
    }

    private void executeSync(Runnable task) {
        if (isMainThread()) {
            task.run();
        } else {
            CompletableFuture<Void> future = new CompletableFuture<>();
            Bukkit.getScheduler().runTask(getPlatformImpl().getPlugin(), () -> {
                try {
                    task.run();
                    future.complete(null);
                } catch (Throwable t) {
                    future.completeExceptionally(t);
                }
            });
            future.join();
        }
    }

    private void applyLightPoints(ServerLevel worldServer, StarLightInterface starLightInterface, StarLightEngine sle,
            ChunkPos chunkPos, Set<LightPos> lightPoints) {
        int type = (sle instanceof BlockStarLightEngine) ? LightFlag.BLOCK_LIGHTING : LightFlag.SKY_LIGHTING;
        int chunkX = chunkPos.x;
        int chunkZ = chunkPos.z;
        if (!worldServer.getChunkSource().isChunkLoaded(chunkX, chunkZ)) {
            return;
        }
        try {
            starEngine_setupCaches.invoke(sle, worldServer.getChunkSource(), chunkX * 16 + 7, 128, chunkZ * 16 + 7,
                    true, true);
            try {
                Iterator<LightPos> it = lightPoints.iterator();
                while (it.hasNext()) {
                    LightPos lightPos = it.next();
                    it.remove();
                    BlockPos blockPos = lightPos.blockPos;
                    int lightLevel = lightPos.lightLevel;
                    int currentLightLevel = getRawLightLevel(worldServer.getWorld(), blockPos.getX(),
                            blockPos.getY(), blockPos.getZ(), type);
                    if (lightLevel <= currentLightLevel) {
                        continue;
                    }
                    int encodeOffset = starEngine_coordinateOffset.getInt(sle);
                    BlockState blockData = worldServer.getBlockState(blockPos);
                    starEngine_setLightLevel.invoke(sle, blockPos.getX(), blockPos.getY(), blockPos.getZ(),
                            lightLevel);
                    if (lightLevel != 0) {
                        starEngine_appendToIncreaseQueue.invoke(sle,
                                ((blockPos.getX() + (blockPos.getZ() << 6) + (blockPos.getY() << (6 + 6))
                                        + encodeOffset) & ((1L << (6 + 6 + 16)) - 1))
                                        | (lightLevel & 0xFL) << (6 + 6 + 16)
                                        | (((long) ALL_DIRECTIONS_BITSET) << (6 + 6 + 16 + 4))
                                        | (((StarlightAbstractBlockState) blockData).starlight$isConditionallyFullOpaque() ? FLAG_HAS_SIDED_TRANSPARENT_BLOCKS : 0));
                    }
                }
                starEngine_performLightIncrease.invoke(sle, worldServer.getChunkSource());
                starEngine_updateVisible.invoke(sle, worldServer.getChunkSource());
            } finally {
                starEngine_destroyCaches.invoke(sle);
            }
        } catch (InvocationTargetException e) {
            throw toRuntimeException(e.getCause());
        } catch (IllegalAccessException e) {
            throw toRuntimeException(e);
        }
    }

    @Override
    public void onInitialization(BukkitPlatformImpl impl) throws Exception {
        super.onInitialization(impl);
        try {
            starEngine_setLightLevel = StarLightEngine.class.getDeclaredMethod("setLightLevel", int.class, int.class,
                    int.class, int.class);
            starEngine_appendToIncreaseQueue = StarLightEngine.class.getDeclaredMethod("appendToIncreaseQueue",
                    long.class);
            starEngine_performLightIncrease = StarLightEngine.class.getDeclaredMethod("performLightIncrease",
                    net.minecraft.world.level.chunk.LightChunkGetter.class);
            starEngine_updateVisible = StarLightEngine.class.getDeclaredMethod("updateVisible",
                    net.minecraft.world.level.chunk.LightChunkGetter.class);
            starEngine_setupCaches = StarLightEngine.class.getDeclaredMethod("setupCaches",
                    net.minecraft.world.level.chunk.LightChunkGetter.class, int.class, int.class, int.class,
                    boolean.class, boolean.class);
            starEngine_destroyCaches = StarLightEngine.class.getDeclaredMethod("destroyCaches");
            starEngine_coordinateOffset = StarLightEngine.class.getDeclaredField("coordinateOffset");
            for (Method m : new Method[] {starEngine_setLightLevel, starEngine_appendToIncreaseQueue,
                    starEngine_performLightIncrease, starEngine_updateVisible, starEngine_setupCaches,
                    starEngine_destroyCaches}) {
                m.setAccessible(true);
            }
            starEngine_coordinateOffset.setAccessible(true);
            impl.info("Handler initialization is done");
        } catch (Exception e) {
            throw toRuntimeException(e);
        }
    }

    @Override
    public LightEngineType getLightEngineType() {
        return LightEngineType.STARLIGHT;
    }

    @Override
    public boolean isLightingSupported(World world, int lightFlags) {
        ServerLevel worldServer = ((CraftWorld) world).getHandle();
        ThreadedLevelLightEngine lightEngine = worldServer.getChunkSource().getLightEngine();
        if (FlagUtils.isFlagSet(lightFlags, LightFlag.SKY_LIGHTING)) {
            return lightEngine.getLayerListener(LightLayer.SKY) != null;
        } else if (FlagUtils.isFlagSet(lightFlags, LightFlag.BLOCK_LIGHTING)) {
            return lightEngine.getLayerListener(LightLayer.BLOCK) != null;
        }
        return false;
    }

    private void removeQueuedLight(Map<ChunkPos, Set<LightPos>> map, ChunkPos chunkPos, BlockPos position) {
        Set<LightPos> points = map.get(chunkPos);
        if (points != null) {
            points.removeIf(lp -> lp.blockPos.equals(position));
        }
    }

    private void queueLight(Map<ChunkPos, Set<LightPos>> map, ChunkPos chunkPos, BlockPos position, int level) {
        map.computeIfAbsent(chunkPos, k -> ConcurrentHashMap.newKeySet()).add(new LightPos(position, level));
    }

    @Override
    public int setRawLightLevel(World world, int blockX, int blockY, int blockZ, int lightLevel, int flags) {
        ServerLevel worldServer = ((CraftWorld) world).getHandle();
        final BlockPos position = new BlockPos(blockX, blockY, blockZ);
        final ThreadedLevelLightEngine lightEngine = worldServer.getChunkSource().getLightEngine();
        final int finalLightLevel = lightLevel < 0 ? 0 : Math.min(lightLevel, 15);
        ChunkPos chunkPos = new ChunkPos(blockX >> 4, blockZ >> 4);

        if (!worldServer.getChunkSource().isChunkLoaded(blockX >> 4, blockZ >> 4)) {
            return ResultCode.CHUNK_NOT_LOADED;
        }

        executeSync(() -> {
            boolean block = FlagUtils.isFlagSet(flags, LightFlag.BLOCK_LIGHTING)
                    && isLightingSupported(world, LightFlag.BLOCK_LIGHTING);
            boolean sky = FlagUtils.isFlagSet(flags, LightFlag.SKY_LIGHTING)
                    && isLightingSupported(world, LightFlag.SKY_LIGHTING);
            if (finalLightLevel == 0) {
                if (block || sky) {
                    // drop a pending (not yet applied) light at this position, otherwise it would re-appear later
                    removeQueuedLight(blockQueueMap, chunkPos, position);
                    removeQueuedLight(skyQueueMap, chunkPos, position);
                    StarLightInterface starLightInterface = getStarInterface(lightEngine);
                    starLightInterface.blockChange(position);
                    starLightInterface.propagateChanges();
                }
            } else {
                if (block) {
                    queueLight(blockQueueMap, chunkPos, position, finalLightLevel);
                }
                if (sky) {
                    queueLight(skyQueueMap, chunkPos, position, finalLightLevel);
                }
            }
        });

        Map<ChunkPos, Set<LightPos>> targetMap = FlagUtils.isFlagSet(flags, LightFlag.SKY_LIGHTING) ? skyQueueMap
                : blockQueueMap;
        if (lightEngine.hasLightWork() || targetMap.containsKey(chunkPos)) {
            return ResultCode.SUCCESS;
        }
        return ResultCode.FAILED;
    }

    @Override
    public int recalculateLighting(World world, int blockX, int blockY, int blockZ, int flags) {
        ServerLevel worldServer = ((CraftWorld) world).getHandle();
        final ThreadedLevelLightEngine lightEngine = worldServer.getChunkSource().getLightEngine();

        if (!worldServer.getChunkSource().isChunkLoaded(blockX >> 4, blockZ >> 4)) {
            return ResultCode.CHUNK_NOT_LOADED;
        }

        // Do not recalculate if no changes!
        if (!lightEngine.hasLightWork() && !getStarInterface(lightEngine).hasUpdates() && blockQueueMap.isEmpty()
                && skyQueueMap.isEmpty()) {
            return ResultCode.RECALCULATE_NO_CHANGES;
        }

        executeSync(() -> {
            StarLightInterface starLightInterface = getStarInterface(lightEngine);
            Iterator<Map.Entry<ChunkPos, Set<LightPos>>> blockIt = blockQueueMap.entrySet().iterator();
            while (blockIt.hasNext()) {
                Map.Entry<ChunkPos, Set<LightPos>> pair = blockIt.next();
                BlockStarLightEngine bsle = starLightInterface.getBlockLightEngine();
                try {
                    applyLightPoints(worldServer, starLightInterface, bsle, pair.getKey(), pair.getValue());
                } finally {
                    starLightInterface.releaseBlockLightEngine(bsle);
                    blockIt.remove();
                }
            }
            Iterator<Map.Entry<ChunkPos, Set<LightPos>>> skyIt = skyQueueMap.entrySet().iterator();
            while (skyIt.hasNext()) {
                Map.Entry<ChunkPos, Set<LightPos>> pair = skyIt.next();
                SkyStarLightEngine ssle = starLightInterface.getSkyLightEngine();
                try {
                    applyLightPoints(worldServer, starLightInterface, ssle, pair.getKey(), pair.getValue());
                } finally {
                    starLightInterface.releaseSkyLightEngine(ssle);
                    skyIt.remove();
                }
            }
            starLightInterface.propagateChanges();
        });
        return ResultCode.SUCCESS;
    }

    private static final class LightPos {

        public final BlockPos blockPos;
        public final int lightLevel;

        public LightPos(BlockPos blockPos, int lightLevel) {
            this.blockPos = blockPos;
            this.lightLevel = lightLevel;
        }
    }
}
