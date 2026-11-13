import pathlib
p = pathlib.Path('src/main/java/com/example/fpvdrone/client/ClientDroneState.java')
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(r'''package com.example.fpvdrone.client;

import com.example.fpvdrone.client.audio.DroneMotorSoundInstance;
import com.example.fpvdrone.client.audio.SignalStaticSoundInstance;
import com.example.fpvdrone.client.gui.FpvHudOverlay;
import com.example.fpvdrone.entity.FpvDroneEntity;
import com.example.fpvdrone.item.FpvGogglesItem;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;

import java.util.UUID;

public class ClientDroneState {
    public static final float MAX_RANGE_METERS = 800.0F; // 50 chunks = 800 blocks

    public enum Phase {
        IDLE,
        PILOTING,
        FREEZE_FRAME,
        NO_SIGNAL
    }

    private static Phase phase = Phase.IDLE;
    private static int activeDroneId = -1;
    private static UUID activeDroneUuid = null;
    private static float throttle = 0.0F;
    private static float batteryVoltage = 16.8F;
    private static int flightTicks = 0;
    private static float distanceMeters = 0.0F;
    private static int phaseTimerTicks = 0;

    private static float lastCamYaw = 0.0F;
    private static float lastCamPitch = 0.0F;
    private static float lastCamRoll = 0.0F;

    private static DroneMotorSoundInstance motorSound;
    private static SignalStaticSoundInstance staticSound;

    public static Phase getPhase() {
        return phase;
    }

    public static int getActiveDroneId() {
        return activeDroneId;
    }

    public static float getThrottle() {
        return throttle;
    }

    public static float getBatteryVoltage() {
        return batteryVoltage;
    }

    public static int getFlightTicks() {
        return flightTicks;
    }

    public static float getDistanceMeters() {
        return distanceMeters;
    }

    public static float getLastCamYaw() {
        return lastCamYaw;
    }

    public static float getLastCamPitch() {
        return lastCamPitch;
    }

    public static float getLastCamRoll() {
        return lastCamRoll;
    }

    public static void setLastCamAngles(float yaw, float pitch, float roll) {
        lastCamYaw = yaw;
        lastCamPitch = pitch;
        lastCamRoll = roll;
    }

    public static boolean isPiloting() {
        return phase == Phase.PILOTING;
    }

    public static boolean isPilotingOrTransitioning() {
        return phase != Phase.IDLE;
    }

    public static void onTelemetryReceived(int droneId, UUID droneUuid, float newThrottle,
                                            float newBattery, int newFlightTicks, boolean initialBind) {
        Minecraft mc = Minecraft.getInstance();
        if (initialBind) {
            phase = Phase.PILOTING;
            activeDroneId = droneId;
            activeDroneUuid = droneUuid;
            phaseTimerTicks = 0;
            if (mc.level != null) {
                Entity e = mc.level.getEntity(droneId);
                if (e instanceof FpvDroneEntity drone) {
                    mc.setCameraEntity(drone);
                    startMotorSound(drone);
                }
            }
        }
        if (phase == Phase.PILOTING && (activeDroneId == droneId || initialBind)) {
            throttle = newThrottle;
            batteryVoltage = newBattery;
            flightTicks = newFlightTicks;
        }
    }

    public static void onDroneDestroyed(int droneEntityId, double ix, double iy, double iz) {
        Minecraft mc = Minecraft.getInstance();
        if (phase != Phase.PILOTING || activeDroneId != droneEntityId || mc.player == null) {
            return;
        }
        if (!(mc.player.getItemBySlot(EquipmentSlot.HEAD).getItem() instanceof FpvGogglesItem)) {
            resetImmediate();
            return;
        }
        triggerSignalLost();
    }

    public static void triggerSignalLost() {
        if (phase != Phase.PILOTING) {
            return;
        }
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || !(mc.player.getItemBySlot(EquipmentSlot.HEAD).getItem() instanceof FpvGogglesItem)) {
            resetImmediate();
            return;
        }
        FpvHudOverlay.captureFreezeFrame();
        stopMotorSound();
        phase = Phase.FREEZE_FRAME;
        phaseTimerTicks = 10; // 0.5 seconds at 20 TPS
        if (mc.getCameraEntity() == null) {
            mc.setCameraEntity(mc.player);
        }
    }

    public static void tick() {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null) {
            resetImmediate();
            return;
        }

        if (phase == Phase.PILOTING) {
            if (!(mc.player.getItemBySlot(EquipmentSlot.HEAD).getItem() instanceof FpvGogglesItem)) {
                resetImmediate();
                return;
            }
            Entity entity = mc.level.getEntity(activeDroneId);
            if (!(entity instanceof FpvDroneEntity drone) || drone.isRemoved()) {
                triggerSignalLost();
                return;
            }
            if (mc.getCameraEntity() != drone) {
                mc.setCameraEntity(drone);
            }
            if (motorSound == null || motorSound.isStopped()) {
                startMotorSound(drone);
            }
            distanceMeters = (float) mc.player.position().distanceTo(drone.position());
            if (distanceMeters >= MAX_RANGE_METERS) {
                triggerSignalLost();
                return;
            }
        } else if (phase == Phase.FREEZE_FRAME) {
            phaseTimerTicks--;
            if (phaseTimerTicks <= 0) {
                phase = Phase.NO_SIGNAL;
                phaseTimerTicks = 40; // 2.0 seconds (0.5s -> 2.5s)
                startStaticSound();
            }
        } else if (phase == Phase.NO_SIGNAL) {
            phaseTimerTicks--;
            if (phaseTimerTicks <= 0) {
                resetImmediate();
            }
        }
    }

    public static void resetImmediate() {
        Minecraft mc = Minecraft.getInstance();
        phase = Phase.IDLE;
        activeDroneId = -1;
        activeDroneUuid = null;
        throttle = 0.0F;
        distanceMeters = 0.0F;
        phaseTimerTicks = 0;
        stopMotorSound();
        stopStaticSound();
        FpvHudOverlay.clearFreezeFrame();
        if (mc.player != null && mc.getCameraEntity() != mc.player) {
            mc.setCameraEntity(mc.player);
        }
    }

    private static void startMotorSound(FpvDroneEntity drone) {
        stopMotorSound();
        motorSound = new DroneMotorSoundInstance(drone);
        Minecraft.getInstance().getSoundManager().play(motorSound);
    }

    private static void stopMotorSound() {
        if (motorSound != null) {
            motorSound.stopSound();
            motorSound = null;
        }
    }

    private static void startStaticSound() {
        stopStaticSound();
        staticSound = new SignalStaticSoundInstance();
        Minecraft.getInstance().getSoundManager().play(staticSound);
    }

    private static void stopStaticSound() {
        if (staticSound != null) {
            staticSound.stopSound();
            staticSound = null;
        }
    }
}
''', encoding="utf-8")
print("Patched", p)
