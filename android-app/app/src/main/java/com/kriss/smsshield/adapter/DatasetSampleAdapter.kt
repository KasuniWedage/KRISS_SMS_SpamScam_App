package com.kriss.smsshield.adapter

import android.content.res.ColorStateList
import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.kriss.smsshield.R
import com.kriss.smsshield.databinding.ItemDatasetSampleBinding
import com.kriss.smsshield.model.DatasetSampleItem

class DatasetSampleAdapter(
    private val onApproveClick: (DatasetSampleItem) -> Unit,
    private val onRejectClick: (DatasetSampleItem) -> Unit
) : ListAdapter<DatasetSampleItem, DatasetSampleAdapter.ViewHolder>(DiffCallback) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemDatasetSampleBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class ViewHolder(private val b: ItemDatasetSampleBinding) : RecyclerView.ViewHolder(b.root) {
        fun bind(item: DatasetSampleItem) {
            b.tvSampleId.text = "#Sample ${item.id}${if (item.smsId != null) " (SMS #${item.smsId})" else ""}"
            b.tvLanguageBadge.text = item.language
            b.tvSampleMessage.text = item.message
            b.tvExpectedLabel.text = "Target: ${item.expectedLabel ?: "Unlabeled"}"

            // Status Styling
            when (item.status.lowercase()) {
                "approved" -> {
                    b.tvStatusBadge.text = "APPROVED"
                    b.tvStatusBadge.setTextColor(ContextCompat.getColor(itemView.context, R.color.success))
                    b.btnApproveSample.visibility = View.GONE
                    b.btnRejectSample.visibility = View.VISIBLE
                    b.btnRejectSample.text = "Reject"
                }
                "rejected" -> {
                    b.tvStatusBadge.text = "REJECTED"
                    b.tvStatusBadge.setTextColor(ContextCompat.getColor(itemView.context, R.color.danger))
                    b.btnApproveSample.visibility = View.VISIBLE
                    b.btnApproveSample.text = "Approve"
                    b.btnRejectSample.visibility = View.GONE
                }
                else -> {
                    b.tvStatusBadge.text = "PENDING"
                    b.tvStatusBadge.setTextColor(ContextCompat.getColor(itemView.context, R.color.warning))
                    b.btnApproveSample.visibility = View.VISIBLE
                    b.btnApproveSample.text = "Approve"
                    b.btnRejectSample.visibility = View.VISIBLE
                    b.btnRejectSample.text = "Reject"
                }
            }

            // Duplicate Detection
            if (item.duplicateCount > 1) {
                b.tvDuplicateBadge.visibility = View.VISIBLE
                b.tvDuplicateBadge.text = "⚠️ ${item.duplicateCount} Duplicates"
            } else {
                b.tvDuplicateBadge.visibility = View.GONE
            }

            b.btnApproveSample.setOnClickListener { onApproveClick(item) }
            b.btnRejectSample.setOnClickListener { onRejectClick(item) }
        }
    }

    companion object DiffCallback : DiffUtil.ItemCallback<DatasetSampleItem>() {
        override fun areItemsTheSame(oldItem: DatasetSampleItem, newItem: DatasetSampleItem): Boolean {
            return oldItem.id == newItem.id
        }

        override fun areContentsTheSame(oldItem: DatasetSampleItem, newItem: DatasetSampleItem): Boolean {
            return oldItem == newItem
        }
    }
}
