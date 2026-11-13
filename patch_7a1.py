import pathlib
PATCH = {
    'src/main/java/com/example/fpvdrone/network/S2CDroneDestroyedPacket.java': r'''package com.example.fpvdrone.network;

import com.example.fpvdrone.client.ClientDroneState;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

import java.util.function.Supplier;

public class S2CDroneDestroyedPacket {
    private final int droneEntityId;
    private final double impactX;
    private final double impactY;
    private final double impactZ;

    public S2CDroneDestroyedPacket(int droneEntityId, double impactX, double impactY, double impactZ) {
        this.droneEntityId = droneEntityId;
        this.impactX = impactX;
        this.impactY = impactY;
        this.impactZ = impactZ;
    }

    public static void encode(S2CDroneDestroyedPacket msg, FriendlyByteBuf buf) {
        buf.writeInt(msg.droneEntityId);
        buf.writeDouble(msg.impactX);
        buf.writeDouble(msg.impactY);
        buf.writeDouble(msg.impactZ);
    }

    public static S2CDroneDestroyedPacket decode(FriendlyByteBuf buf) {
        return new S2CDroneDestroyedPacket(buf.readInt(), buf.readDouble(), buf.readDouble(), buf.readDouble());
    }

    public static void handle(S2CDroneDestroyedPacket msg, Supplier<NetworkEvent.Context> ctxSupplier) {
        NetworkEvent.Context ctx = ctxSupplier.get();
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () ->
                ClientDroneState.onDroneDestroyed(msg.droneEntityId, msg.impactX, msg.impactY, msg.impactZ));
        ctx.setPacketHandled(true);
    }
}
''',
    'src/main/java/com/example/fpvdrone/client/renderer/FpvDroneRenderer.java': r'''package com.example.fpvdrone.client.renderer;

import com.example.fpvdrone.client.ClientDroneState;
import com.example.fpvdrone.entity.FpvDroneEntity;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import org.joml.Quaternionf;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

public class FpvDroneRenderer extends GeoEntityRenderer<FpvDroneEntity> {
    public FpvDroneRenderer(EntityRendererProvider.Context renderManager) {
        super(renderManager, new FpvDroneModel());
        this.shadowRadius = 0.35F;
    }

    @Override
    public void render(FpvDroneEntity entity, float entityYaw, float partialTick,
                       PoseStack poseStack, MultiBufferSource bufferSource, int packedLight) {
        Minecraft mc = Minecraft.getInstance();
        if (ClientDroneState.isPiloting()
                && mc.options.getCameraType().isFirstPerson()
                && mc.getCameraEntity() == entity) {
            return;
        }

        poseStack.pushPose();
        poseStack.translate(0.0D, 0.15D, 0.0D);
        Quaternionf q = entity.getInterpolatedOrientation(partialTick);
        poseStack.mulPose(q);
        // Rotate 180 deg around Y so the -Z model nose/warhead faces +Z flight forward
        poseStack.mulPose(Axis.YP.rotationDegrees(180.0F));
        poseStack.translate(0.0D, -0.15D, 0.0D);
        super.render(entity, entityYaw, partialTick, poseStack, bufferSource, packedLight);
        poseStack.popPose();
    }
}
''',
}
for k, v in PATCH.items():
    p = pathlib.Path(k)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(v, encoding="utf-8")
print("Patched", len(PATCH), "files")
