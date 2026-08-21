package com.eva.homeassist

import android.graphics.Bitmap
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.MultipartBody
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit


const val COOLDOWN_TIME_MS = 1 * 60 * 1000L

class DetectionUploadState {
    var isPresent: Boolean = false
    var hasUploadedCurrentSession: Boolean = false
    var cooldownUntil: Long = 0L
}

fun uploadImageToBackend(bitmap: Bitmap, onResult: (String, String?) -> Unit) {
    CoroutineScope(Dispatchers.IO).launch {
        try {
            val stream = ByteArrayOutputStream()
            bitmap.compress(Bitmap.CompressFormat.JPEG, 85, stream)
            val byteArray = stream.toByteArray()

            val client = OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(120, TimeUnit.SECONDS)
                .build()

            val requestBody = MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart(
                    "file",
                    "capture.jpg",
                    byteArray.toRequestBody("image/jpeg".toMediaTypeOrNull())
                )
                .build()

            val request = Request.Builder()
                .url(BuildConfig.DETECTION_URL)
                .post(requestBody)
                .build()

            client.newCall(request).execute().use { response ->
                if (response.isSuccessful) {
                    val responseString = response.body?.string() ?: "{}"
                    val jsonObject = JSONObject(responseString)
                    val inferenceResult = jsonObject.optString("inference", "Got no text.")
                    val audioUrl = jsonObject.optString("audio_url", "").takeIf { it.isNotEmpty() }

                    withContext(Dispatchers.Main) {
                        onResult(inferenceResult, audioUrl)
                    }
                } else {
                    withContext(Dispatchers.Main) {
                        onResult("Server error: ${response.code}", null)
                    }
                }
            }
        } catch (e: Exception) {
            withContext(Dispatchers.Main) {
                onResult("Network error: ${e.message}", null)
            }
        }
    }
}