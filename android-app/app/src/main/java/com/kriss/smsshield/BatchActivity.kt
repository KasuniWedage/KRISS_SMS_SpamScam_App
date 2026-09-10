package com.kriss.smsshield

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.kriss.smsshield.api.AuthGuard
import com.kriss.smsshield.api.RetrofitClient
import com.kriss.smsshield.databinding.ActivityBatchBinding
import com.kriss.smsshield.model.BatchRequest
import com.kriss.smsshield.model.ClassificationRequest
import com.kriss.smsshield.report.BatchAnalysisPdfReport
import com.kriss.smsshield.report.BatchHistoryStore
import com.kriss.smsshield.report.BatchReportData
import kotlinx.coroutines.launch

class BatchActivity : AppCompatActivity() {
    private lateinit var b: ActivityBatchBinding
    private var currentReport: BatchReportData? = null
    private val createPdf=registerForActivityResult(ActivityResultContracts.CreateDocument("application/pdf")){uri->
        val report=currentReport
        if(uri!=null&&report!=null)try{contentResolver.openOutputStream(uri)?.use{BatchAnalysisPdfReport.write(this,report,it)}?:error("destination");Toast.makeText(this,R.string.pdf_saved,Toast.LENGTH_LONG).show()}catch(_:Exception){Toast.makeText(this,R.string.pdf_failed,Toast.LENGTH_LONG).show()}
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityBatchBinding.inflate(layoutInflater)
        setContentView(b.root)
        b.batchBackIcon.setOnClickListener { finish() }
        b.batchButton.setOnClickListener { classifyBatch() }
        b.downloadBatchReportButton.setOnClickListener { chooseReportLanguage() }
        b.batchHistoryButton.setOnClickListener { startActivity(Intent(this,BatchHistoryActivity::class.java)) }
    }

    private fun classifyBatch() {
        if (!b.batchButton.isEnabled) return
        val messages = b.batchInput.text.toString().lines().map { it.trim() }.filter { it.isNotEmpty() }
        if (messages.isEmpty()) {
            b.batchResult.setText(R.string.batch_empty_error)
            return
        }
        if (messages.size > 100) {
            b.batchResult.setText(R.string.batch_limit_error)
            return
        }
        b.loading.visibility = View.VISIBLE
        b.batchButton.isEnabled = false
        b.batchResult.text = getString(R.string.batch_processing, messages.size)
        lifecycleScope.launch {
            try {
                val request = BatchRequest(messages.map { ClassificationRequest(it) })
                val r = RetrofitClient.api(this@BatchActivity).classifyBatch(request)
                if (r.isSuccessful) {
                    val result = r.body().orEmpty()
                    val report = BatchHistoryStore.fromResults(messages, result)
                    currentReport = report
                    BatchHistoryStore.save(this@BatchActivity, report)
                    b.downloadBatchReportButton.visibility = View.VISIBLE
                    b.batchResult.text = result.mapIndexed { index, x ->
                        val marker = when (x.label) {
                            "Scam" -> "\uD83D\uDD34"
                            "Spam" -> "\uD83D\uDFE0"
                            else -> "\uD83D\uDFE2"
                        }
                        val localizedLabel = when (x.label.lowercase()) {
                            "scam" -> getString(R.string.label_scam)
                            "spam" -> getString(R.string.label_spam)
                            else -> getString(R.string.label_legitimate)
                        }
                        "$marker ${index + 1}. $localizedLabel (${String.format("%.2f", x.confidence)}%)\n     ${messages[index].take(70)}"
                    }.joinToString("\n\n")
                } else if (r.code() == 401) {
                    AuthGuard.redirectToLogin(this@BatchActivity)
                } else {
                    b.batchResult.text = getString(R.string.batch_failed, r.code())
                }
            } catch (e: Exception) {
                b.batchResult.text = getString(R.string.backend_connection_error, e.localizedMessage.orEmpty())
            } finally {
                b.loading.visibility = View.GONE
                b.batchButton.isEnabled = true
            }
        }
    }

    private fun chooseReportLanguage() {
        val report = currentReport ?: return
        val languages = arrayOf(
            getString(R.string.language_english),
            getString(R.string.language_sinhala),
            getString(R.string.language_tamil)
        )
        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.choose_report_language)
            .setItems(languages) { _, i ->
                val langCode = when (i) {
                    1 -> "si"
                    2 -> "ta"
                    else -> "en"
                }
                currentReport = report.copy(reportLanguage = langCode)
                createPdf.launch("KRISS-Batch-Report-${report.id}.pdf")
            }
            .setNegativeButton(R.string.cancel, null)
            .show()
    }
}
