package com.eva.homeassist

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.animateOffsetAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.eva.homeassist.ui.theme.HomeAssistTheme
import android.view.WindowManager
import androidx.compose.runtime.mutableLongStateOf
import kotlinx.coroutines.delay

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        enableEdgeToEdge()
        setContent {
            HomeAssistTheme {
                MainScreen()
            }
        }
    }
}

@Composable
fun MainScreen() {
    val context = LocalContext.current
    var hasCameraPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
        onResult = { granted -> hasCameraPermission = granted }
    )

    LaunchedEffect(Unit) {
        if (!hasCameraPermission) {
            permissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    var rawLookOffset by remember { mutableStateOf(Offset.Zero) }
    var isPersonDetected by remember { mutableStateOf(false) }
    var rawPersonScale by remember { mutableFloatStateOf(0f) }
    var aiMessage by remember { mutableStateOf("") }
    var isTalking by remember { mutableStateOf(false) }

    var cooldownExpiration by remember { mutableLongStateOf(0L) }
    var isCooling by remember { mutableStateOf(false) }

    val animatedLookOffset by animateOffsetAsState(
        targetValue = rawLookOffset,
        animationSpec = spring(dampingRatio = 0.7f, stiffness = Spring.StiffnessLow),
        label = "eyeTrackingAnimation"
    )

    LaunchedEffect(cooldownExpiration) {
        val now = System.currentTimeMillis()
        if (cooldownExpiration > now) {
            isCooling = true
            delay((cooldownExpiration - now).milliseconds)
            isCooling = false
        } else {
            isCooling = false
        }
    }

    val animatedPersonScale by animateFloatAsState(
        targetValue = rawPersonScale,
        animationSpec = spring(dampingRatio = 0.7f, stiffness = Spring.StiffnessLow),
        label = "pupilDilationAnimation"
    )

    Box(modifier = Modifier.fillMaxSize().background(Color(0xFF1E1E1E))) {

        StylizedTrackingFaceBackground(
            modifier = Modifier.fillMaxSize(),
            lookOffset = animatedLookOffset,
            isPersonDetected = isPersonDetected,
            personScale = animatedPersonScale,
            isTalking = isTalking,
            isCooling = isCooling
        )

        Box(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(top = 48.dp, end = 16.dp)
                .size(120.dp, 160.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(Color.Black)
        ) {
            if (hasCameraPermission) {
                FrontCameraPreview(
                    modifier = Modifier.fillMaxSize(),
                    onPersonDetected = { normalizedOffset, detected, scale ->
                        rawLookOffset = normalizedOffset
                        isPersonDetected = detected
                        rawPersonScale = scale
                    },
                    onInferenceResult = { resultText, audioUrl ->
                        aiMessage = resultText
                        if (audioUrl != null) {
                            AudioPlayer.play(
                                url = audioUrl,
                                onStart = { isTalking = true },
                                onComplete = { isTalking = false }
                            )
                        }
                    },
                    onCooldownActivated = { newExpirationTime ->
                        cooldownExpiration = newExpirationTime
                    }
                )
            } else {
                Text("No Permission", color = Color.White, modifier = Modifier.align(Alignment.Center))
            }
        }
    }
}