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
import net.minecraft.core.SectionPos;
import net.minecraft.network.protocol.game.ClientboundLightUpdatePacket;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.ThreadedLevelLightEngine;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.LightLayer;
import net.minecraft.world.level.chunk.LevelChunk;

import org.bukkit.Bukkit;
import org.bukkit.World;
import org.bukkit.craftbukkit.CraftWorld;
import org.bukkit.event.world.WorldLoadEvent;
import org.bukkit.event.world.WorldUnloadEvent;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.BitSet;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Stream;

import ru.beykerykt.minecraft.lightapi.bukkit.internal.BukkitPlatformImpl;
import ru.beykerykt.minecraft.lightapi.bukkit.internal.handler.craftbukkit.nms.BaseNMSHandler;
import ru.beykerykt.minecraft.lightapi.common.api.ResultCode;
import ru.beykerykt.minecraft.lightapi.common.api.engine.LightFlag;
import ru.beykerykt.minecraft.lightapi.common.internal.chunks.data.BitChunkData;
import ru.beykerykt.minecraft.lightapi.common.internal.chunks.data.IChunkData;
import ru.beykerykt.minecraft.lightapi.common.internal.engine.LightEngineType;
import ru.beykerykt.minecraft.lightapi.common.internal.engine.LightEngineVersion;
import ru.beykerykt.minecraft.lightapi.common.internal.utils.FlagUtils;

public abstract class VanillaNMSHandler extends BaseNMSHandler {

    protected static RuntimeException toRuntimeException(Throwable e) {
        if (e instanceof RuntimeException) {
            return (RuntimeException) e;
        }
        Class<? extends Throwable> cls = e.getClass();
        return new RuntimeException(String.format("(%s) %s",
                RuntimeException.class.getPackage().equals(cls.getPackage()) ? cls.getSimpleName() : cls.getName(),
                e.getMessage()), e);
    }

    private int getDeltaLight(int x, int dx) {
        return (((x ^ ((-dx >> 4) & 15)) + 1) & (-(dx & 1)));
    }

    private IChunkData createBitChunkData(String worldName, int chunkX, int chunkZ) {
        World world = Bukkit.getWorld(worldName);
        ServerLevel worldServer = ((CraftWorld) world).getHandle();
        final ThreadedLevelLightEngine lightEngine = worldServer.getChunkSource().getLightEngine();
        int bottom = lightEngine.getMinLightSection();
        int top = lightEngine.getMaxLightSection();
        return new BitChunkData(worldName, chunkX, chunkZ, top, bottom);
    }

    @Override
    public void onShutdown(BukkitPlatformImpl impl) {
    }

    @Override
    public LightEngineType getLightEngineType() {
        return LightEngineType.VANILLA;
    }

    @Override
    public void onWorldLoad(WorldLoadEvent event) {
    }

    @Override
    public void onWorldUnload(WorldUnloadEvent event) {
    }

    @Override
    public LightEngineVersion getLightEngineVersion() {
        return LightEngineVersion.V2;
    }

    @Override
    public int getRawLightLevel(World world, int blockX, int blockY, int blockZ, int flags) {
        int lightLevel = -1;
        ServerLevel worldServer = ((CraftWorld) world).getHandle();
        BlockPos position = new BlockPos(blockX, blockY, blockZ);
        if (FlagUtils.isFlagSet(flags, LightFlag.BLOCK_LIGHTING) && FlagUtils.isFlagSet(flags,
                LightFlag.SKY_LIGHTING)) {
            lightLevel = worldServer.getLightEmission(position);
        } else if (FlagUtils.isFlagSet(flags, LightFlag.BLOCK_LIGHTING)) {
            lightLevel = worldServer.getBrightness(LightLayer.BLOCK, position);
        } else if (FlagUtils.isFlagSet(flags, LightFlag.SKY_LIGHTING)) {
            lightLevel = worldServer.getBrightness(LightLayer.SKY, position);
        }
        return lightLevel;
    }

    @Override
    public IChunkData createChunkData(String worldName, int chunkX, int chunkZ) {
        return createBitChunkData(worldName, chunkX, chunkZ);
    }

    private IChunkData searchChunkDataFromList(List<IChunkData> list, World world, int chunkX, int chunkZ) {
        for (IChunkData data : list) {
            if (data.getWorldName().equals(world.getName()) && data.getChunkX() == chunkX
                    && data.getChunkZ() == chunkZ) {
                return data;
            }
        }
        return createChunkData(world.getName(), chunkX, chunkZ);
    }

    @Override
    public List<IChunkData> collectChunkSections(World world, int blockX, int blockY, int blockZ, int lightLevel,
            int lightFlags) {
        ServerLevel worldServer = ((CraftWorld) world).getHandle();
        List<IChunkData> list = new ArrayList<>();
        int finalLightLevel = lightLevel < 0 ? 0 : Math.min(lightLevel, 15);

        if (world == null) {
            return list;
        }

        for (int dX = -1; dX <= 1; dX++) {
            int lightLevelX = finalLightLevel - getDeltaLight(blockX & 15, dX);
            if (lightLevelX > 0) {
                for (int dZ = -1; dZ <= 1; dZ++) {
                    int lightLevelZ = lightLevelX - getDeltaLight(blockZ & 15, dZ);
                    if (lightLevelZ > 0) {
                        int chunkX = (blockX >> 4) + dX;
                        int chunkZ = (blockZ >> 4) + dZ;
                        if (!worldServer.getChunkSource().isChunkLoaded(chunkX, chunkZ)) {
                            continue;
                        }
                        for (int dY = -1; dY <= 1; dY++) {
                            if (lightLevelZ > getDeltaLight(blockY & 15, dY)) {
                                int sectionY = (blockY >> 4) + dY;
                                if (isValidChunkSection(world, sectionY)) {
                                    IChunkData data = searchChunkDataFromList(list, world, chunkX, chunkZ);
                                    if (!list.contains(data)) {
                                        list.add(data);
                                    }
                                    data.markSectionForUpdate(lightFlags, sectionY);
                                }
                            }
                        }
                    }
                }
            }
        }
        return list;
    }

    @Override
    public boolean isValidChunkSection(World world, int sectionY) {
        ServerLevel worldServer = ((CraftWorld) world).getHandle();
        ThreadedLevelLightEngine lightEngine = worldServer.getChunkSource().getLightEngine();
        return (sectionY >= lightEngine.getMinLightSection()) && (sectionY <= lightEngine.getMaxLightSection());
    }

    @Override
    public int sendChunk(IChunkData data) {
        World world = Bukkit.getWorld(data.getWorldName());
        if (data instanceof BitChunkData) {
            BitChunkData icd = (BitChunkData) data;
            return sendChunk(world, icd.getChunkX(), icd.getChunkZ(), icd.getSkyLightUpdateBits(),
                    icd.getBlockLightUpdateBits());
        }
        return ResultCode.NOT_IMPLEMENTED;
    }

    protected int sendChunk(World world, int chunkX, int chunkZ, BitSet sectionMaskSky, BitSet sectionMaskBlock) {
        if (world == null) {
            return ResultCode.WORLD_NOT_AVAILABLE;
        }
        ServerLevel worldServer = ((CraftWorld) world).getHandle();
        if (!worldServer.getChunkSource().isChunkLoaded(chunkX, chunkZ)) {
            return ResultCode.CHUNK_NOT_LOADED;
        }
        LevelChunk chunk = worldServer.getChunk(chunkX, chunkZ);
        ChunkPos chunkCoordIntPair = chunk.getPos();
        Stream<ServerPlayer> stream = worldServer.getChunkSource().chunkMap.getPlayers(chunkCoordIntPair,
                false).stream();
        ClientboundLightUpdatePacket packet = new ClientboundLightUpdatePacket(chunk.getPos(),
                chunk.getLevel().getLightEngine(), sectionMaskSky, sectionMaskBlock);
        stream.forEach(e -> e.connection.send(packet));
        return ResultCode.SUCCESS;
    }

    @Override
    public int sendCmd(int cmdId, Object... args) {
        return 0;
    }
}