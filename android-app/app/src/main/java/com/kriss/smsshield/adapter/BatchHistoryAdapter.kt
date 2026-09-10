package com.kriss.smsshield.adapter

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.kriss.smsshield.R
import com.kriss.smsshield.databinding.ItemBatchHistoryBinding
import com.kriss.smsshield.report.BatchReportData
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class BatchHistoryAdapter(
    private val items: List<BatchReportData>,
    private val onView: (BatchReportData) -> Unit,
    private val onDownload: (BatchReportData) -> Unit,
    private val onDelete: (BatchReportData) -> Unit
) : RecyclerView.Adapter<BatchHistoryAdapter.Holder>() {
    class Holder(val binding: ItemBatchHistoryBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) = Holder(
        ItemBatchHistoryBinding.inflate(LayoutInflater.from(parent.context), parent, false)
    )

    override fun getItemCount() = items.size

    override fun onBindViewHolder(holder: Holder, position: Int) {
        val report = items[position]
        val threats = report.items.count {
            it.label.equals("Spam", true) || it.label.equals("Scam", true)
        }
        val safe = report.items.size - threats
        val spam = report.items.count { it.label.equals("Spam", true) }
        val scam = report.items.count { it.label.equals("Scam", true) }
        holder.binding.dateText.text = SimpleDateFormat(
            "dd MMM yyyy • HH:mm", Locale.getDefault()
        ).format(Date(report.createdAt))
        holder.binding.summaryText.text = holder.itemView.context.getString(
            R.string.batch_history_summary, report.items.size, threats
        )
        holder.binding.safeCount.text = holder.itemView.context.getString(R.string.safe_count, safe)
        holder.binding.spamCount.text = holder.itemView.context.getString(R.string.spam_count, spam)
        holder.binding.scamCount.text = holder.itemView.context.getString(R.string.scam_count, scam)
        holder.binding.root.setOnClickListener { onView(report) }
        holder.binding.viewResultsButton.setOnClickListener { onView(report) }
        holder.binding.downloadButton.setOnClickListener { onDownload(report) }
        holder.binding.deleteButton.setOnClickListener { onDelete(report) }
    }
}
