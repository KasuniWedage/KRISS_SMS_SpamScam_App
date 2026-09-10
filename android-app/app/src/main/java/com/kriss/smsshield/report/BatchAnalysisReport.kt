package com.kriss.smsshield.report

import android.content.Context
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.kriss.smsshield.R
import com.kriss.smsshield.model.ClassificationResponse
import java.io.OutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class BatchReportItem(val smsId:Int,val message:String,val label:String,val confidence:Double,val language:String,val scamType:String?,val explanation:String)
data class BatchReportData(val id:Long,val createdAt:Long,val items:List<BatchReportItem>,val reportLanguage:String="en",val batchId:String="")

object BatchHistoryStore {
    private const val LEGACY_FILE = "kriss_batch_history"
    private const val ENCRYPTED_FILE = "kriss_secure_batch_history"
    private const val KEY = "runs"

    private fun getPrefs(context: Context): SharedPreferences {
        return try {
            EncryptedSharedPreferences.create(
                ENCRYPTED_FILE,
                MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC),
                context.applicationContext,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
        } catch (_: Throwable) {
            context.applicationContext.getSharedPreferences(LEGACY_FILE, Context.MODE_PRIVATE)
        }
    }

    private fun storedJson(context: Context): String? {
        return try {
            val prefs = getPrefs(context)
            val data = prefs.getString(KEY, null)
            if (!data.isNullOrBlank()) {
                data
            } else {
                val legacy = context.applicationContext.getSharedPreferences(LEGACY_FILE, Context.MODE_PRIVATE)
                legacy.getString(KEY, null)
            }
        } catch (_: Throwable) {
            try {
                val legacy = context.applicationContext.getSharedPreferences(LEGACY_FILE, Context.MODE_PRIVATE)
                legacy.getString(KEY, null)
            } catch (_: Throwable) {
                null
            }
        }
    }

    fun save(context: Context, report: BatchReportData) {
        try {
            val existing = list(context).filterNot {
                it.id == report.id || (Math.abs(it.createdAt - report.createdAt) < 5000 && it.items.map { item -> item.message } == report.items.map { item -> item.message })
            }
            val runs = mutableListOf(report).apply {
                addAll(existing)
                if (size > 50) subList(50, size).clear()
            }
            val json = Gson().toJson(runs)
            try {
                getPrefs(context).edit().putString(KEY, json).commit()
            } catch (_: Throwable) {}
            try {
                context.applicationContext.getSharedPreferences(LEGACY_FILE, Context.MODE_PRIVATE)
                    .edit().putString(KEY, json).commit()
            } catch (_: Throwable) {}
        } catch (e: Throwable) {
            android.util.Log.e("BatchHistoryStore", "Failed to save batch report", e)
        }
    }

    fun list(context: Context): List<BatchReportData> {
        val json = storedJson(context) ?: return emptyList()
        val raw = runCatching {
            Gson().fromJson<List<BatchReportData>>(json, object : TypeToken<List<BatchReportData>>() {}.type)
        }.getOrDefault(emptyList())

        val unique = mutableListOf<BatchReportData>()
        for (item in raw) {
            val isDuplicate = unique.any { existing ->
                existing.id == item.id || (
                    Math.abs(existing.createdAt - item.createdAt) < 5000 &&
                    existing.items.map { it.message } == item.items.map { it.message }
                )
            }
            if (!isDuplicate) unique.add(item)
        }
        return unique
    }

    fun delete(context: Context, batchId: Long): Boolean {
        return try {
            val runs = list(context).filterNot { it.id == batchId }
            if (runs.isEmpty()) {
                clear(context)
            } else {
                val json = Gson().toJson(runs)
                getPrefs(context).edit().putString(KEY, json).commit()
                context.applicationContext.getSharedPreferences(LEGACY_FILE, Context.MODE_PRIVATE)
                    .edit().putString(KEY, json).commit()
                true
            }
        } catch (_: Throwable) {
            false
        }
    }

    fun clear(context: Context): Boolean {
        return try {
            val p1 = getPrefs(context).edit().remove(KEY).commit()
            val p2 = context.applicationContext.getSharedPreferences(LEGACY_FILE, Context.MODE_PRIVATE)
                .edit().remove(KEY).commit()
            p1 || p2
        } catch (_: Throwable) {
            false
        }
    }

    fun fromResults(messages: List<String>, results: List<ClassificationResponse>) = BatchReportData(
        id = System.currentTimeMillis(),
        createdAt = System.currentTimeMillis(),
        items = results.mapIndexed { i, x ->
            BatchReportItem(
                smsId = x.smsId,
                message = messages.getOrElse(i) { "" },
                label = x.label,
                confidence = x.confidence,
                language = x.language,
                scamType = x.scamType,
                explanation = x.explanation
            )
        }
    )

    fun fromApiResponse(res: com.kriss.smsshield.model.BatchHistoryResponse): BatchReportData {
        val createdMillis = try {
            SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US).parse(res.createdAt.substringBefore("."))?.time ?: System.currentTimeMillis()
        } catch (_: Throwable) {
            System.currentTimeMillis()
        }
        return BatchReportData(
            id = res.id.toLong(),
            createdAt = createdMillis,
            items = res.items.map {
                BatchReportItem(
                    smsId = it.smsId,
                    message = it.message,
                    label = it.label,
                    confidence = it.confidence,
                    language = it.language,
                    scamType = it.scamType,
                    explanation = it.explanation
                )
            },
            reportLanguage = res.reportLanguage,
            batchId = res.batchId
        )
    }
}

object BatchAnalysisPdfReport {
    private const val W=595
    private const val H=842
    private const val M=38f
    fun write(context:Context, report:BatchReportData, output:OutputStream) {
        val doc=PdfDocument()
        val chunks=if(report.items.isEmpty()) listOf(emptyList()) else listOf(report.items.take(6))+report.items.drop(6).chunked(7)
        chunks.forEachIndexed { pageIndex,items ->
            val page=doc.startPage(PdfDocument.PageInfo.Builder(W,H,pageIndex+1).create())
            drawPage(context,page.canvas,report,items,pageIndex+1,chunks.size)
            doc.finishPage(page)
        }
        doc.writeTo(output);doc.close()
    }
    private fun drawPage(context: Context, c: android.graphics.Canvas, r: BatchReportData, items: List<BatchReportItem>, page: Int, pages: Int) {
        val lang = r.reportLanguage.lowercase(Locale.ROOT)
        fun t(en: String, sn: String, ta: String) = when (lang) {
            "si" -> sn
            "ta" -> ta
            else -> en
        }
        val p = Paint(Paint.ANTI_ALIAS_FLAG).apply { typeface = Typeface.create("sans-serif", Typeface.NORMAL) }
        c.drawColor(Color.rgb(248, 250, 252))
        p.color = Color.rgb(4, 28, 68)
        c.drawRect(0f, 0f, W.toFloat(), 148f, p)
        p.color = Color.WHITE
        c.drawRoundRect(RectF(449f, 12f, 565f, 137f), 15f, 15f, p)
        BitmapFactory.decodeResource(context.resources, R.drawable.kriss_full_logo)?.let {
            c.drawBitmap(it, null, Rect(457, 18, 557, 131), p)
        }
        p.color = Color.WHITE
        p.typeface = Typeface.DEFAULT_BOLD
        p.textSize = 19f
        c.drawText(t("BATCH ANALYSIS REPORT", "සමූහ විශ්ලේෂණ වාර්තාව", "தொகுதி பகுப்பாய்வு அறிக்கை"), M, 48f, p)
        p.typeface = Typeface.DEFAULT
        p.textSize = 10f
        c.drawText("#KB-${r.id.toString().takeLast(8)}", M, 72f, p)
        val locale = when (lang) {
            "si" -> Locale.forLanguageTag("si")
            "ta" -> Locale.forLanguageTag("ta")
            else -> Locale.ENGLISH
        }
        c.drawText(SimpleDateFormat("dd MMM yyyy • HH:mm", locale).format(Date(r.createdAt)), M, 91f, p)
        c.drawText(t("Page $page of $pages", "පිටුව $page / $pages", "பக்கம் $page / $pages"), M, 118f, p)
        val scam = r.items.count { it.label.equals("Scam", true) }
        val spam = r.items.count { it.label.equals("Spam", true) }
        val safe = r.items.size - scam - spam
        var y = 174f
        if (page == 1) {
            summary(c, p, t("TOTAL", "මුළු", "மொத்தம்"), r.items.size, M, y, Color.rgb(7, 90, 166))
            summary(c, p, t("SAFE", "ආරක්ෂිත", "பாதுகாப்பானது"), safe, 170f, y, Color.rgb(22, 163, 74))
            summary(c, p, t("THREATS", "අවදානම්", "அச்சுறுத்தல்கள்"), spam + scam, 302f, y, Color.rgb(220, 38, 38))
            y += 92f
        }
        p.color = Color.rgb(15, 23, 42)
        p.typeface = Typeface.DEFAULT_BOLD
        p.textSize = 11f
        c.drawText(t("MESSAGE RESULTS", "පණිවිඩ ප්‍රතිඵල", "செய்தி முடிவுகள்"), M, y, p)
        y += 22f
        items.forEachIndexed { i, x ->
            val color = when (x.label.lowercase()) {
                "scam" -> Color.rgb(220, 38, 38)
                "spam" -> Color.rgb(217, 119, 6)
                else -> Color.rgb(22, 163, 74)
            }
            p.color = Color.WHITE
            c.drawRoundRect(RectF(M, y, W - M, y + 68f), 12f, 12f, p)
            p.color = color
            c.drawRoundRect(RectF(M, y, M + 5f, y + 68f), 5f, 5f, p)
            p.color = Color.rgb(15, 23, 42)
            p.typeface = Typeface.DEFAULT_BOLD
            p.textSize = 10f
            val label = when (x.label.lowercase()) {
                "scam" -> t("SCAM", "වංචා", "மோசடி")
                "spam" -> t("SPAM", "ස්පෑම්", "ஸ்பேம்")
                else -> t("LEGITIMATE", "සාමාන්‍ය", "சாதாரணமானது")
            }
            c.drawText("${(page - 1) * 7 + i + 1}. $label • ${"%.1f".format(Locale.US, x.confidence)}%", M + 14f, y + 20f, p)
            p.typeface = Typeface.DEFAULT
            p.textSize = 9f
            p.color = Color.rgb(71, 85, 105)
            c.drawText(x.message.replace('\n', ' ').take(92), M + 14f, y + 40f, p)
            c.drawText(t("Language", "භාෂාව", "மொழி") + ": ${x.language}" + (x.scamType?.let { "  •  $it" } ?: ""), M + 14f, y + 57f, p)
            y += 78f
        }
        p.color = Color.rgb(100, 116, 139)
        p.textSize = 8f
        c.drawText(t("Generated by KRISS SMS Shield • Review suspicious messages carefully.", "KRISS SMS Shield මගින් ජනනය කරන ලදී • සැක සහිත පණිවිඩ ප්‍රවේශමෙන් බලන්න.", "KRISS SMS Shield மூலம் உருவாக்கப்பட்டது • சந்தேகத்திற்கிடமான செய்திகளை கவனமாக மதிப்பாய்வு செய்யவும்."), M, 820f, p)
    }
    private fun summary(c:android.graphics.Canvas,p:Paint,title:String,value:Int,x:Float,y:Float,color:Int){p.color=Color.WHITE;c.drawRoundRect(RectF(x,y,x+116f,y+68f),12f,12f,p);p.color=color;p.typeface=Typeface.DEFAULT_BOLD;p.textSize=20f;c.drawText(value.toString(),x+14f,y+30f,p);p.textSize=8.5f;c.drawText(title,x+14f,y+51f,p)}
}
