package com.kriss.smsshield

import android.os.Bundle
import android.widget.Toast
import android.view.View
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import androidx.appcompat.app.AppCompatActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.kriss.smsshield.api.RetrofitClient
import com.kriss.smsshield.databinding.ActivityResultBinding
import com.kriss.smsshield.model.FeedbackRequest
import com.kriss.smsshield.model.ReportRequest
import com.kriss.smsshield.model.PublishSpamRequest
import com.kriss.smsshield.report.AnalysisPdfReport
import com.kriss.smsshield.report.AnalysisReportData
import kotlinx.coroutines.launch

class ResultActivity : AppCompatActivity() {
    private lateinit var b: ActivityResultBinding
    private var smsId = 0
    private lateinit var reportData: AnalysisReportData
    private val createPdf = registerForActivityResult(ActivityResultContracts.CreateDocument("application/pdf")) { uri ->
        if (uri == null) return@registerForActivityResult
        try {
            contentResolver.openOutputStream(uri)?.use { AnalysisPdfReport.write(this@ResultActivity, reportData, it) }
                ?: error("Unable to open destination")
            Toast.makeText(this, R.string.pdf_saved, Toast.LENGTH_LONG).show()
        } catch (_: Exception) {
            Toast.makeText(this, R.string.pdf_failed, Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityResultBinding.inflate(layoutInflater)
        setContentView(b.root)

        smsId = intent.getIntExtra("smsId", 0)
        val label = intent.getStringExtra("label") ?: "Unknown"
        val conf = intent.getDoubleExtra("confidence", 0.0)
        val lang = intent.getStringExtra("language") ?: "Unknown"
        val scam = intent.getStringExtra("scamType")
        val exp = intent.getStringExtra("explanation") ?: ""
        val ruleOverride = intent.getBooleanExtra("ruleOverride", false)
        val message = intent.getStringExtra("message").orEmpty()
        val sender = intent.getStringExtra("sender")

        reportData = AnalysisReportData(smsId, label, conf, lang, scam, exp, message, sender, ruleOverride)

        b.labelText.text = when (label.lowercase()) {
            "scam" -> getString(R.string.label_scam)
            "spam" -> getString(R.string.label_spam)
            else -> getString(R.string.label_legitimate)
        }
        b.confidenceText.text = getString(R.string.result_confidence_value, conf)
        b.confidenceBar.progress = conf.toInt().coerceIn(0, 100)
        b.languageText.text = getString(R.string.result_language_value, lang)
        b.decisionSourceText.text = getString(if (ruleOverride) R.string.result_source_hybrid else R.string.result_source_ml)

        if (scam.isNullOrBlank()) {
            b.scamTypePill.visibility = View.GONE
        } else {
            b.scamTypeText.text = scam
        }

        b.explanationText.text = exp
        b.resultBackIcon.setOnClickListener { finish() }

        when (label) {
            "Scam" -> {
                b.resultHeader.setBackgroundResource(R.drawable.bg_header_danger)
                b.resultIcon.setImageResource(R.drawable.ic_error)
                b.resultIcon.imageTintList = ContextCompat.getColorStateList(this, R.color.white)
                b.confidenceBar.progressDrawable = ContextCompat.getDrawable(this, R.drawable.progress_rounded_danger)
                b.warningBanner.setBackgroundResource(R.drawable.bg_pill_danger)
                b.warningIcon.imageTintList = ContextCompat.getColorStateList(this, R.color.danger)
                b.warningText.setTextColor(ContextCompat.getColor(this, R.color.danger))
                b.warningText.setText(R.string.result_warning_scam)
            }
            "Spam" -> {
                b.resultHeader.setBackgroundResource(R.drawable.bg_header_warning)
                b.resultIcon.setImageResource(R.drawable.ic_alert_triangle)
                b.resultIcon.imageTintList = ContextCompat.getColorStateList(this, R.color.white)
                b.confidenceBar.progressDrawable = ContextCompat.getDrawable(this, R.drawable.progress_rounded_warning)
                b.warningBanner.setBackgroundResource(R.drawable.bg_pill_warning)
                b.warningIcon.imageTintList = ContextCompat.getColorStateList(this, R.color.warning)
                b.warningText.setTextColor(ContextCompat.getColor(this, R.color.warning))
                b.warningText.setText(R.string.result_warning_spam)
            }
            else -> {
                b.resultHeader.setBackgroundResource(R.drawable.bg_header_safe)
                b.resultIcon.setImageResource(R.drawable.ic_check_circle)
                b.resultIcon.imageTintList = ContextCompat.getColorStateList(this, R.color.white)
                b.confidenceBar.progressDrawable = ContextCompat.getDrawable(this, R.drawable.progress_rounded_success)
                b.warningBanner.setBackgroundResource(R.drawable.bg_pill_safe)
                b.warningIcon.imageTintList = ContextCompat.getColorStateList(this, R.color.success)
                b.warningText.setTextColor(ContextCompat.getColor(this, R.color.success))
                b.warningText.setText(R.string.result_warning_safe)
                b.reportButton.visibility = View.GONE
                b.publishButton.visibility = View.GONE
            }
        }

        b.reportButton.setOnClickListener { showReport() }
        b.feedbackButton.setOnClickListener { showFeedback(label) }
        b.downloadPdfButton.setOnClickListener { choosePdfLanguage() }
        b.publishButton.setOnClickListener { publishToCommunity(message, sender, label) }
        b.backButton.setOnClickListener { finish() }
    }

    private fun publishToCommunity(message:String,sender:String?,label:String){
        if(sender.isNullOrBlank()){Toast.makeText(this,R.string.sender_required,Toast.LENGTH_LONG).show();return}
        if(label.equals("Legitimate",true)||label.equals("Safe",true))return
        MaterialAlertDialogBuilder(this).setTitle(R.string.publish_confirm_title).setMessage(R.string.publish_confirm_message)
            .setNegativeButton(R.string.cancel,null).setPositiveButton(R.string.publish){_,_->lifecycleScope.launch{
                try{val r=RetrofitClient.api(this@ResultActivity).publishSpam(PublishSpamRequest(smsId,sender,message));if(r.code()==401){com.kriss.smsshield.api.AuthGuard.redirectToLogin(this@ResultActivity);return@launch};Toast.makeText(this@ResultActivity,if(r.isSuccessful)R.string.publish_success else R.string.publish_failed,Toast.LENGTH_LONG).show();if(r.isSuccessful)b.publishButton.isEnabled=false}catch(_:Exception){Toast.makeText(this@ResultActivity,R.string.publish_failed,Toast.LENGTH_LONG).show()}
            }}.show()
    }

    private fun choosePdfLanguage() {
        val languages = arrayOf(
            getString(R.string.language_english),
            getString(R.string.language_sinhala),
            getString(R.string.language_tamil)
        )
        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.choose_report_language)
            .setItems(languages) { _, index ->
                val code = when (index) {
                    1 -> "si"
                    2 -> "ta"
                    else -> "en"
                }
                reportData = reportData.copy(reportLanguage = code)
                val stamp = java.text.SimpleDateFormat("yyyyMMdd-HHmm", java.util.Locale.US).format(java.util.Date())
                createPdf.launch("KRISS-SMS-Report-$stamp.pdf")
            }
            .setNegativeButton(R.string.cancel, null)
            .show()
    }

    private fun showReport() {
        val input = EditText(this).apply { setHint(R.string.report_reason_hint) }
        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.report_dialog_title)
            .setView(input)
            .setNegativeButton(R.string.cancel, null)
            .setPositiveButton(R.string.report_submit) { _, _ ->
                val reason = input.text.toString().trim().ifBlank { getString(R.string.report_default_reason) }
                lifecycleScope.launch {
                    try {
                        val r = RetrofitClient.api(this@ResultActivity).report(ReportRequest(smsId, reason))
                        b.feedbackStatusText.setText(if (r.isSuccessful) R.string.report_success else R.string.report_failed)
                    } catch (_: Exception) {
                        b.feedbackStatusText.setText(R.string.report_failed)
                    }
                }
            }.show()
    }

    private fun showFeedback(currentLabel: String) {
        val labels = listOf(getString(R.string.feedback_correct, currentLabel), getString(R.string.label_legitimate), getString(R.string.label_spam), getString(R.string.label_scam))
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 12, 48, 0)
        }
        val spinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@ResultActivity, android.R.layout.simple_spinner_dropdown_item, labels)
        }
        val input = EditText(this).apply { setHint(R.string.feedback_optional) }
        container.addView(spinner)
        container.addView(input)
        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.feedback_dialog_title)
            .setMessage(R.string.feedback_dialog_message)
            .setView(container)
            .setNegativeButton(R.string.cancel, null)
            .setPositiveButton(R.string.submit) { _, _ ->
                val expected = when (spinner.selectedItemPosition) { 0 -> currentLabel; 1 -> "Legitimate"; 2 -> "Spam"; else -> "Scam" }
                lifecycleScope.launch {
                    try {
                        val r = RetrofitClient.api(this@ResultActivity).feedback(
                            FeedbackRequest(smsId, input.text.toString().trim().ifBlank { null }, expected)
                        )
                        b.feedbackStatusText.setText(if (r.isSuccessful) R.string.feedback_success else R.string.feedback_failed)
                    } catch (_: Exception) {
                        b.feedbackStatusText.setText(R.string.feedback_failed)
                    }
                }
            }.show()
    }
}
