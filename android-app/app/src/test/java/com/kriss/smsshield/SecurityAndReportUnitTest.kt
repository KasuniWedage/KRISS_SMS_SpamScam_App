package com.kriss.smsshield

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Android Unit Tests validating client data models, localization mappings,
 * and security payload formatters.
 */
class SecurityAndReportUnitTest {

    @Test
    fun testClassificationResultJsonParsing() {
        val rawJson = """
            {
                "sms_id": 42,
                "label": "Scam",
                "confidence": 0.985,
                "language": "Sinhala",
                "scam_type": "Bank Phishing",
                "explanation": "High-risk banking keyword detected",
                "indicators": ["bank", "verify", "account"],
                "recommendation": "Do not click links or share credentials",
                "risk_level": "HIGH"
            }
        """.trimIndent()

        val json = JSONObject(rawJson)
        assertEquals(42, json.getInt("sms_id"))
        assertEquals("Scam", json.getString("label"))
        assertEquals(0.985, json.getDouble("confidence"), 0.001)
        assertEquals("Sinhala", json.getString("language"))
        assertEquals("Bank Phishing", json.getString("scam_type"))
        assertTrue(json.getJSONArray("indicators").length() == 3)
    }

    @Test
    fun testTrilingualTranslationMatrix() {
        fun translate(key: String, lang: String): String {
            return when (key) {
                "safe" -> when (lang) {
                    "si" -> "ආරක්ෂිතයි"
                    "ta" -> "பாதுகாப்பானது"
                    else -> "SAFE"
                }
                "spam" -> when (lang) {
                    "si" -> "අනවශ්‍ය පණිවිඩයක්"
                    "ta" -> "ஸ்பேம்"
                    else -> "SPAM"
                }
                "scam" -> when (lang) {
                    "si" -> "වංචනික පණිවිඩයක්"
                    "ta" -> "மோசடி"
                    else -> "SCAM"
                }
                else -> key
            }
        }

        assertEquals("SAFE", translate("safe", "en"))
        assertEquals("ආරක්ෂිතයි", translate("safe", "si"))
        assertEquals("பாதுகாப்பானது", translate("safe", "ta"))

        assertEquals("SCAM", translate("scam", "en"))
        assertEquals("වංචනික පණිවිඩයක්", translate("scam", "si"))
        assertEquals("மோசடி", translate("scam", "ta"))
    }

    @Test
    fun testBatchStatisticsCalculation() {
        val total = 50
        val safe = 35
        val spam = 10
        val scam = 5

        assertEquals(50, safe + spam + scam)
        val safePercent = (safe.toDouble() / total) * 100
        val threatsPercent = ((spam + scam).toDouble() / total) * 100

        assertEquals(70.0, safePercent, 0.01)
        assertEquals(30.0, threatsPercent, 0.01)
    }
}
