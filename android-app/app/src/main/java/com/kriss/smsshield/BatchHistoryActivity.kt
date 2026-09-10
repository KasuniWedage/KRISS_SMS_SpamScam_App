package com.kriss.smsshield

import android.os.Bundle
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.kriss.smsshield.adapter.BatchHistoryAdapter
import com.kriss.smsshield.databinding.ActivityBatchHistoryBinding
import com.kriss.smsshield.databinding.DialogBatchDetailsBinding
import com.kriss.smsshield.report.BatchAnalysisPdfReport
import com.kriss.smsshield.report.BatchHistoryStore
import com.kriss.smsshield.report.BatchReportData

import androidx.lifecycle.lifecycleScope
import com.kriss.smsshield.api.RetrofitClient
import kotlinx.coroutines.launch

class BatchHistoryActivity : AppCompatActivity() {
    private lateinit var binding: ActivityBatchHistoryBinding
    private var selected: BatchReportData? = null

    private val createPdf = registerForActivityResult(
        ActivityResultContracts.CreateDocument("application/pdf")
    ) { uri ->
        val report = selected
        if (uri != null && report != null) {
            try {
                contentResolver.openOutputStream(uri)?.use {
                    BatchAnalysisPdfReport.write(this, report, it)
                } ?: error("Unable to open destination")
                Toast.makeText(this, R.string.pdf_saved, Toast.LENGTH_LONG).show()
            } catch (_: Exception) {
                Toast.makeText(this, R.string.pdf_failed, Toast.LENGTH_LONG).show()
            }
        }
        selected = null
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBatchHistoryBinding.inflate(layoutInflater)
        setContentView(binding.root)
        binding.backButton.setOnClickListener { finish() }
        binding.clearAllButton.setOnClickListener { confirmClearAll() }
        binding.historyList.layoutManager = LinearLayoutManager(this)
        loadHistory()
    }

    override fun onResume() {
        super.onResume()
        loadHistory()
    }

    private fun displayRuns(runs: List<BatchReportData>) {
        binding.emptyText.visibility = if (runs.isEmpty()) View.VISIBLE else View.GONE
        binding.clearAllButton.visibility = if (runs.isEmpty()) View.GONE else View.VISIBLE
        binding.historyList.adapter = BatchHistoryAdapter(runs, ::showDetails, ::chooseLanguage, ::confirmDelete)
    }

    private fun loadHistory() {
        val cached = BatchHistoryStore.list(this)
        displayRuns(cached)

        lifecycleScope.launch {
            try {
                val res = RetrofitClient.api(this@BatchHistoryActivity).getBatchHistory(limit = 100)
                if (res.isSuccessful && res.body() != null) {
                    val serverRuns = res.body()!!.map { BatchHistoryStore.fromApiResponse(it) }
                    for (item in serverRuns) {
                        BatchHistoryStore.save(this@BatchHistoryActivity, item)
                    }
                    val combined = if (serverRuns.isNotEmpty()) serverRuns else BatchHistoryStore.list(this@BatchHistoryActivity)
                    displayRuns(combined)
                }
            } catch (_: Exception) {
                // Offline fallback already rendered
            }
        }
    }

    private fun confirmDelete(report: BatchReportData) {
        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.delete_batch_confirm_title)
            .setMessage(R.string.delete_batch_confirm_message)
            .setPositiveButton(R.string.delete) { _, _ ->
                BatchHistoryStore.delete(this, report.id)
                lifecycleScope.launch {
                    try {
                        val key = if (report.batchId.isNotBlank()) report.batchId else report.id.toString()
                        RetrofitClient.api(this@BatchHistoryActivity).deleteBatchHistory(key)
                    } catch (_: Exception) {}
                }
                Toast.makeText(this, R.string.batch_deleted, Toast.LENGTH_SHORT).show()
                loadHistory()
            }
            .setNegativeButton(R.string.cancel, null)
            .show()
    }

    private fun confirmClearAll() {
        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.clear_batch_history_confirm_title)
            .setMessage(R.string.clear_batch_history_confirm_message)
            .setPositiveButton(R.string.delete) { _, _ ->
                BatchHistoryStore.clear(this)
                lifecycleScope.launch {
                    try {
                        RetrofitClient.api(this@BatchHistoryActivity).clearBatchHistory()
                    } catch (_: Exception) {}
                }
                Toast.makeText(this, R.string.all_batch_history_cleared, Toast.LENGTH_SHORT).show()
                loadHistory()
            }
            .setNegativeButton(R.string.cancel, null)
            .show()
    }

    private fun showDetails(report: BatchReportData) {
        val safe = report.items.count {
            it.label.equals("Safe", true) || it.label.equals("Legitimate", true)
        }
        val spam = report.items.count { it.label.equals("Spam", true) }
        val scam = report.items.count { it.label.equals("Scam", true) }
        val details = report.items.mapIndexed { index, item ->
            val label = when (item.label.lowercase()) {
                "scam" -> getString(R.string.label_scam)
                "spam" -> getString(R.string.label_spam)
                else -> getString(R.string.label_legitimate)
            }
            buildString {
                append("${index + 1}. $label • ${"%.1f".format(item.confidence)}%\n")
                append(item.message)
                append("\n${getString(R.string.language_label)}: ${item.language}")
                item.scamType?.takeIf { it.isNotBlank() }?.let { append(" • $it") }
                item.explanation.takeIf { it.isNotBlank() }?.let { append("\n$it") }
            }
        }.joinToString("\n\n")

        val dialogBinding = DialogBatchDetailsBinding.inflate(layoutInflater)
        dialogBinding.safeSummary.text = getString(R.string.safe_count, safe)
        dialogBinding.spamSummary.text = getString(R.string.spam_count, spam)
        dialogBinding.scamSummary.text = getString(R.string.scam_count, scam)
        dialogBinding.detailsText.text = details
        val dialog = MaterialAlertDialogBuilder(this).setView(dialogBinding.root).create()
        dialogBinding.closeButton.setOnClickListener { dialog.dismiss() }
        dialogBinding.downloadButton.setOnClickListener {
            dialog.dismiss()
            chooseLanguage(report)
        }
        dialog.setOnShowListener {
            dialog.window?.setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))
        }
        dialog.show()
    }

    private fun chooseLanguage(report: BatchReportData) {
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
                selected = report.copy(reportLanguage = code)
                createPdf.launch("KRISS-Batch-Report-${report.id}.pdf")
            }
            .setNegativeButton(R.string.cancel, null)
            .show()
    }
}
