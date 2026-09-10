package com.kriss.smsshield.report

import android.graphics.Canvas
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Rect
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import android.content.Context
import com.kriss.smsshield.R
import java.io.OutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class AnalysisReportData(
    val smsId: Int,
    val label: String,
    val confidence: Double,
    val detectedLanguage: String,
    val scamType: String?,
    val explanation: String,
    val message: String,
    val sender: String?,
    val ruleOverride: Boolean,
    val reportLanguage: String = "en"
)

object AnalysisPdfReport {
    private const val PAGE_WIDTH = 595
    private const val PAGE_HEIGHT = 842
    private const val MARGIN = 42f
    private val navy = Color.rgb(15, 23, 42)
    private val indigo = Color.rgb(79, 70, 229)
    private val muted = Color.rgb(100, 116, 139)
    private val line = Color.rgb(226, 232, 240)

    fun write(context: Context, data: AnalysisReportData, output: OutputStream) {
        val document = PdfDocument()
        val page = document.startPage(PdfDocument.PageInfo.Builder(PAGE_WIDTH, PAGE_HEIGHT, 1).create())
        draw(page.canvas, data, context)
        document.finishPage(page)
        document.writeTo(output)
        document.close()
    }

    private fun draw(canvas: Canvas, data: AnalysisReportData, context: Context) {
        val lang = data.reportLanguage.lowercase(Locale.ROOT)
        fun t(en: String, sinhala: String, tamil: String) = when (lang) {
            "si" -> sinhala
            "ta" -> tamil
            else -> en
        }
        fun displayLabel(label: String) = when (label.lowercase(Locale.ROOT)) {
            "scam" -> t("SCAM", "වංචාවක්", "மோசடி")
            "spam" -> t("SPAM", "ස්පෑම්", "ஸ்பேம்")
            else -> t("LEGITIMATE", "සාමාන්‍ය", "சாதாரணமானது")
        }
        val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply { typeface = Typeface.create("sans-serif", Typeface.NORMAL) }
        canvas.drawColor(Color.rgb(248, 250, 252))

        paint.color = navy
        canvas.drawRect(0f, 0f, PAGE_WIDTH.toFloat(), 176f, paint)
        paint.color = indigo
        canvas.drawCircle(530f, 36f, 112f, paint)
        val logoPanel = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE }
        canvas.drawRoundRect(RectF(438f, 14f, 565f, 146f), 16f, 16f, logoPanel)
        val logo = BitmapFactory.decodeResource(context.resources, R.drawable.kriss_full_logo)
        if (logo != null) {
            canvas.drawBitmap(logo, null, Rect(447, 20, 556, 139), paint)
        }
        paint.color = Color.WHITE
        paint.typeface = Typeface.create("sans-serif", Typeface.BOLD)
        paint.textSize = 22f
        canvas.drawText("KRISS SMS SHIELD", MARGIN, 60f, paint)
        paint.textSize = 11f
        paint.typeface = Typeface.create("sans-serif", Typeface.NORMAL)
        canvas.drawText(t("AI MESSAGE SECURITY • ANALYSIS REPORT", "AI පණිවිඩ ආරක්ෂණ • විශ්ලේෂණ වාර්තාව", "AI செய்தி பாதுகாப்பு • பகுப்பாய்வு அறிக்கை"), MARGIN, 82f, paint)
        paint.textSize = 10f
        canvas.drawText(t("Report", "වාර්තාව", "அறிக்கை") + " #KR-${data.smsId.toString().padStart(6, '0')}", MARGIN, 130f, paint)
        val reportLocale = when (lang) {
            "si" -> Locale.forLanguageTag("si")
            "ta" -> Locale.forLanguageTag("ta")
            else -> Locale.ENGLISH
        }
        canvas.drawText(SimpleDateFormat("dd MMM yyyy • HH:mm", reportLocale).format(Date()), MARGIN, 148f, paint)

        roundedCard(canvas, 42f, 154f, 553f, 278f, Color.WHITE, paint)
        val statusColor = when (data.label.lowercase(Locale.ROOT)) {
            "scam" -> Color.rgb(220, 38, 38)
            "spam" -> Color.rgb(217, 119, 6)
            else -> Color.rgb(22, 163, 74)
        }
        paint.color = statusColor
        canvas.drawCircle(92f, 216f, 32f, paint)
        paint.color = Color.WHITE
        paint.textAlign = Paint.Align.CENTER
        paint.typeface = Typeface.create("sans-serif", Typeface.BOLD)
        paint.textSize = 22f
        canvas.drawText("${data.confidence.toInt()}%", 92f, 223f, paint)
        paint.textAlign = Paint.Align.LEFT
        paint.color = muted
        paint.textSize = 10f
        canvas.drawText(t("DETECTION RESULT", "හඳුනාගැනීමේ ප්‍රතිඵලය", "கண்டறிதல் முடிவு"), 144f, 190f, paint)
        paint.color = navy
        paint.textSize = 27f
        canvas.drawText(displayLabel(data.label), 144f, 222f, paint)
        paint.typeface = Typeface.create("sans-serif", Typeface.NORMAL)
        paint.textSize = 10.5f
        paint.color = muted
        canvas.drawText(t("Language", "භාෂාව", "மொழி") + ": ${data.detectedLanguage}", 144f, 246f, paint)
        val unknown = t("Not identified", "හඳුනාගෙන නැත", "அடையாளம் காணப்படவில்லை")
        canvas.drawText(t("Type", "වර්ගය", "வகை") + ": ${data.scamType?.ifBlank { unknown } ?: unknown}", 330f, 246f, paint)

        var y = 312f
        y = section(canvas, paint, t("EXECUTIVE SUMMARY", "සාරාංශය", "நிர்வாக சுருக்கம்"), data.explanation.ifBlank { t("No additional explanation was provided by the detection engine.", "හඳුනාගැනීමේ පද්ධතිය අමතර පැහැදිලි කිරීමක් ලබා දී නැත.", "கண்டறிதல் இயந்திரத்தால் கூடுதல் விளக்கம் வழங்கப்படவில்லை.") }, y)
        y = section(canvas, paint, t("ANALYZED MESSAGE", "විශ්ලේෂණය කළ පණිවිඩය", "பகுப்பாய்வு செய்யப்பட்ட செய்தி"), data.message.ifBlank { t("Message text unavailable.", "පණිවිඩය ලබාගත නොහැක.", "செய்தி உரை கிடைக்கவில்லை.") }, y + 10f)

        paint.color = navy
        paint.typeface = Typeface.create("sans-serif", Typeface.BOLD)
        paint.textSize = 11f
        canvas.drawText(t("ANALYSIS DETAILS", "විශ්ලේෂණ විස්තර", "பகுப்பாய்வு விவரங்கள்"), MARGIN, y + 16f, paint)
        y += 34f
        val source = if (data.ruleOverride) t("High-risk hybrid rules + machine learning", "ඉහළ අවදානම් නීති + යන්ත්‍ර ඉගෙනීම", "உயர் ஆபத்து கலப்பின விதிகள் + இயந்திர கற்றல்") else t("Machine-learning classifier", "යන්ත්‍ර ඉගෙනුම් වර්ගීකාරකය", "இயந்திர கற்றல் வகைப்படுத்தி")
        detailRow(canvas, paint, t("Sender", "යවන්නා", "அனுப்புநர்"), data.sender?.ifBlank { t("Not provided", "ලබා දී නැත", "வழங்கப்படவில்லை") } ?: t("Not provided", "ලබා දී නැත", "வழங்கப்படவில்லை"), y)
        detailRow(canvas, paint, t("Decision source", "තීරණ මූලාශ්‍රය", "முடிவு மூலம்"), source, y + 28f)
        detailRow(canvas, paint, t("Confidence score", "විශ්වාසනීයත්වය", "நம்பகத்தன்மை மதிப்பீடு"), "${"%.2f".format(Locale.US, data.confidence)}%", y + 56f)

        val adviceY = (y + 100f).coerceAtMost(706f)
        roundedCard(canvas, MARGIN, adviceY, PAGE_WIDTH - MARGIN, adviceY + 76f, Color.rgb(238, 242, 255), paint)
        paint.color = indigo
        paint.typeface = Typeface.create("sans-serif", Typeface.BOLD)
        paint.textSize = 11f
        canvas.drawText(t("RECOMMENDED ACTION", "නිර්දේශිත ක්‍රියාමාර්ගය", "பரிந்துரைக்கப்பட்ட நடவடிக்கை"), MARGIN + 16f, adviceY + 24f, paint)
        paint.color = navy
        paint.typeface = Typeface.create("sans-serif", Typeface.NORMAL)
        paint.textSize = 9.5f
        val advice = if (data.label.equals("Legitimate", true))
            t("Remain vigilant. Verify unexpected requests through a trusted channel.", "අවධානයෙන් සිටින්න. අනපේක්ෂිත ඉල්ලීම් විශ්වාසදායක මාර්ගයකින් තහවුරු කරන්න.", "விழிப்புடன் இருங்கள். எதிர்பாராத கோரிக்கைகளை நம்பகமான சேனல் மூலம் சரிபார்க்கவும்.")
        else t("Do not open links, disclose credentials or send money. Verify the sender independently.", "සබැඳි විවෘත කිරීම, රහස් තොරතුරු ලබාදීම හෝ මුදල් යැවීම නොකරන්න. යවන්නා වෙනම තහවුරු කරන්න.", "இணைப்புகளைத் திறக்கவோ, விவரங்களை வெளியிடவோ அல்லது பணம் அனுப்பவோ வேண்டாம். அனுப்புநரைத் தனித்தனியாக சரிபார்க்கவும்.")
        drawWrapped(canvas, advice, MARGIN + 16f, adviceY + 46f, PAGE_WIDTH - MARGIN * 2 - 32f, 13f, paint, 2)

        paint.color = line
        canvas.drawRect(MARGIN, 806f, PAGE_WIDTH - MARGIN, 807f, paint)
        paint.color = muted
        paint.textSize = 8f
        canvas.drawText(t("Generated by KRISS SMS Shield • Automated results support careful judgment.", "KRISS SMS Shield මගින් ජනනය කරන ලදී • ස්වයංක්‍රීය ප්‍රතිඵල ප්‍රවේශමෙන් භාවිත කරන්න.", "KRISS SMS Shield மூலம் உருவாக்கப்பட்டது • கவனமாக முடிவெடுக்க தானியங்கி முடிவுகள் உதவுகின்றன."), MARGIN, 824f, paint)
    }

    private fun section(canvas: Canvas, paint: Paint, title: String, body: String, top: Float): Float {
        paint.color = navy
        paint.typeface = Typeface.create("sans-serif", Typeface.BOLD)
        paint.textSize = 11f
        canvas.drawText(title, MARGIN, top, paint)
        paint.color = muted
        paint.typeface = Typeface.create("sans-serif", Typeface.NORMAL)
        paint.textSize = 10f
        val lines = drawWrapped(canvas, body, MARGIN, top + 22f, PAGE_WIDTH - MARGIN * 2, 15f, paint, 5)
        return top + 30f + lines * 15f
    }

    private fun detailRow(canvas: Canvas, paint: Paint, key: String, value: String, y: Float) {
        paint.color = line
        canvas.drawRect(MARGIN, y + 15f, PAGE_WIDTH - MARGIN, y + 16f, paint)
        paint.color = muted
        paint.typeface = Typeface.create("sans-serif", Typeface.NORMAL)
        paint.textSize = 9.5f
        canvas.drawText(key, MARGIN, y, paint)
        paint.color = navy
        paint.typeface = Typeface.create("sans-serif", Typeface.BOLD)
        canvas.drawText(value.take(58), 190f, y, paint)
    }

    private fun roundedCard(canvas: Canvas, left: Float, top: Float, right: Float, bottom: Float, color: Int, paint: Paint) {
        paint.color = color
        canvas.drawRoundRect(RectF(left, top, right, bottom), 18f, 18f, paint)
    }

    private fun drawWrapped(canvas: Canvas, text: String, x: Float, y: Float, width: Float, spacing: Float, paint: Paint, maxLines: Int): Int {
        val words = text.replace('\n', ' ').split(Regex("\\s+")).filter { it.isNotBlank() }
        var lineText = ""
        val lines = mutableListOf<String>()
        for (word in words) {
            val candidate = if (lineText.isBlank()) word else "$lineText $word"
            if (paint.measureText(candidate) <= width) lineText = candidate else {
                if (lineText.isNotBlank()) lines += lineText
                lineText = word
            }
        }
        if (lineText.isNotBlank()) lines += lineText
        lines.take(maxLines).forEachIndexed { index, value ->
            val visible = if (index == maxLines - 1 && lines.size > maxLines) value.take(80) + "…" else value
            canvas.drawText(visible, x, y + index * spacing, paint)
        }
        return lines.size.coerceAtMost(maxLines).coerceAtLeast(1)
    }
}
