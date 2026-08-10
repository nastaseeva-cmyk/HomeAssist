package com.eva.homeassist

import android.graphics.Bitmap
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL

const val BACKEND_URL = "http://192.168.64.145:7000/detection"
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

            val url = URL(BACKEND_URL)
            val connection = url.openConnection() as HttpURLConnection
            connection.requestMethod = "POST"
            connection.setRequestProperty("Content-Type", "image/jpeg")
            connection.setRequestProperty("Content-Length", byteArray.size.toString())
            connection.doOutput = true

            connection.connectTimeout = 10000
            connection.readTimeout = 120000

            connection.outputStream.use { os ->
                os.write(byteArray)
            }

            if (connection.responseCode == 200) {
                val responseString = connection.inputStream.bufferedReader().use { it.readText() }

                val jsonObject = JSONObject(responseString)
                val inferenceResult = jsonObject.optString("inference", "Got no text.")
                val audioUrl = jsonObject.optString("audio_url", "").takeIf { it.isNotEmpty() }

                withContext(Dispatchers.Main) {
                    onResult(inferenceResult, audioUrl)
                }
            } else {
                withContext(Dispatchers.Main) {
                    onResult("Server error: ${connection.responseCode}", null)
                }
            }
            connection.disconnect()
        } catch (e: Exception) {
            withContext(Dispatchers.Main) {
                onResult("Network error: ${e.message}", null)
            }
        }
    }
}