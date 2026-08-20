package com.eva.homeassist

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import kotlin.math.max

@Composable
fun StylizedTrackingFaceBackground(
    modifier: Modifier = Modifier,
    lookOffset: Offset,
    isPersonDetected: Boolean,
    personScale: Float,
    isTalking: Boolean,
    isCooling: Boolean,
    isListening: Boolean
) {
    val faceColor = if (isCooling) Color.Gray else Color.Cyan
    val earColor = if (isListening) Color.Red else Color.Gray
    val pupilColor = Color.Red
    val strokeWidth = 24f

    val eyeColor by animateColorAsState(
        targetValue = if (isPersonDetected) pupilColor else faceColor.copy(alpha = 0.1f),
        animationSpec = spring(stiffness = Spring.StiffnessLow),
        label = "eyeGlowAnimation"
    )

    val infiniteTransition = rememberInfiniteTransition(label = "mouthTransition")
    val mouthOpenAnim by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "mouthOpenAnim"
    )

    val talkingStateAnim by animateFloatAsState(
        targetValue = if (isTalking) 1f else 0f,
        animationSpec = spring(stiffness = Spring.StiffnessMediumLow),
        label = "talkingState"
    )

    val currentMouthOpen = talkingStateAnim * mouthOpenAnim

    Canvas(modifier = modifier) {
        val canvasWidth = size.width
        val canvasHeight = size.height

        val centerX = canvasWidth * 0.45f
        val faceTopY = canvasHeight * 0.45f
        val faceHeight = canvasHeight * 0.4f

        val eyeY = faceTopY + faceHeight * 0.2f
        val eyeOffsetX = canvasWidth * 0.18f
        val eyeRadius = canvasWidth * 0.12f

        val earY = faceTopY + faceHeight * 0.2f
        val earOffsetX = canvasWidth * 0.40f
        val earOffsetY = canvasHeight * 0.10f
        val earRadius = canvasWidth * 0.05f

        val noseTopY = faceTopY + faceHeight * 0.4f
        val noseBottomY = faceTopY + faceHeight * 0.6f

        val mouthY = faceTopY + faceHeight * 0.85f
        val mouthWidth = canvasWidth * 0.25f

        val minPupilRadius = eyeRadius * 0.2f
        val maxPupilRadius = eyeRadius * 0.75f
        val pupilRadius = if (isPersonDetected) {
            minPupilRadius + (maxPupilRadius - minPupilRadius) * personScale.coerceIn(0f, 1f)
        } else {
            eyeRadius * 0.35f
        }

        val maxLookShift = max(0f, eyeRadius - pupilRadius - (strokeWidth / 2f))

        val actualShiftX = lookOffset.x * maxLookShift
        val actualShiftY = lookOffset.y * maxLookShift

        // eyes
        drawCircle(
            color = faceColor,
            radius = eyeRadius,
            center = Offset(centerX - eyeOffsetX, eyeY),
            style = Stroke(width = strokeWidth)
        )
        drawCircle(
            color = faceColor,
            radius = eyeRadius,
            center = Offset(centerX + eyeOffsetX, eyeY),
            style = Stroke(width = strokeWidth)
        )
        drawCircle(
            color = eyeColor,
            radius = pupilRadius,
            center = Offset(centerX - eyeOffsetX + actualShiftX, eyeY + actualShiftY)
        )
        drawCircle(
            color = eyeColor,
            radius = pupilRadius,
            center = Offset(centerX + eyeOffsetX + actualShiftX, eyeY + actualShiftY)
        )

        // ears
        drawCircle(
            color = earColor,
            radius = earRadius,
            center = Offset(centerX - earOffsetX, earY + earOffsetY)
        )
        drawCircle(
            color = earColor,
            radius = earRadius,
            center = Offset(centerX + earOffsetX, earY + earOffsetY)
        )


        // nose
        drawLine(
            color = faceColor,
            start = Offset(centerX, noseTopY),
            end = Offset(centerX, noseBottomY),
            strokeWidth = strokeWidth
        )

        // mouth
        val maxMouthHeight = canvasWidth * 0.15f
        val mouthHeight = strokeWidth + (maxMouthHeight * currentMouthOpen)

        drawRoundRect(
            color = faceColor,
            topLeft = Offset(centerX - mouthWidth / 2f, mouthY - strokeWidth / 2f),
            size = Size(mouthWidth, mouthHeight),
            cornerRadius = CornerRadius(strokeWidth / 2f, strokeWidth / 2f)
        )
    }
}