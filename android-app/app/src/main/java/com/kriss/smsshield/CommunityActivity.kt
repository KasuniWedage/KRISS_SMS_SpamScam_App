package com.kriss.smsshield
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.kriss.smsshield.adapter.CommunityAdapter
import com.kriss.smsshield.adapter.CommunityDisplayItem
import com.kriss.smsshield.api.AuthGuard
import com.kriss.smsshield.api.RetrofitClient
import com.kriss.smsshield.databinding.ActivityCommunityBinding
import kotlinx.coroutines.launch

class CommunityActivity:AppCompatActivity(){private lateinit var b:ActivityCommunityBinding;private val adapter=CommunityAdapter(emptyList())
 override fun onCreate(s:Bundle?){super.onCreate(s);b=ActivityCommunityBinding.inflate(layoutInflater);setContentView(b.root);b.backButton.setOnClickListener{finish()};b.list.layoutManager=LinearLayoutManager(this);b.list.adapter=adapter;b.tabs.setOnCheckedStateChangeListener{_,ids->when(ids.firstOrNull()){b.reportsTab.id->loadReports();b.feedbackTab.id->loadFeedback();else->loadCommunity()}};when(intent.getStringExtra("tab")){"reports"->b.reportsTab.isChecked=true;"feedback"->b.feedbackTab.isChecked=true;else->loadCommunity()}}
 private fun show(items:List<CommunityDisplayItem>){adapter.submit(items);b.emptyText.visibility=if(items.isEmpty())View.VISIBLE else View.GONE;b.loading.visibility=View.GONE}
 private fun unauthorized(code:Int):Boolean{if(code==401){AuthGuard.redirectToLogin(this);return true};return false}
 private fun loadCommunity(){b.loading.visibility=View.VISIBLE;lifecycleScope.launch{try{val r=RetrofitClient.api(this@CommunityActivity).communitySpam();if(unauthorized(r.code()))return@launch;show(r.body().orEmpty().map{CommunityDisplayItem("${it.label} • ${it.senderNo}",it.message,"Published community warning",it.publishedAt.replace('T',' ').take(19))})}catch(_:Exception){show(emptyList())}}}
 private fun loadReports(){b.loading.visibility=View.VISIBLE;lifecycleScope.launch{try{val r=RetrofitClient.api(this@CommunityActivity).myReports();if(unauthorized(r.code()))return@launch;show(r.body().orEmpty().map{CommunityDisplayItem("Report #${it.id}",it.message,it.reason,it.reportDate.replace('T',' ').take(19))})}catch(_:Exception){show(emptyList())}}}
 private fun loadFeedback(){b.loading.visibility=View.VISIBLE;lifecycleScope.launch{try{val r=RetrofitClient.api(this@CommunityActivity).myFeedback();if(unauthorized(r.code()))return@launch;show(r.body().orEmpty().map{CommunityDisplayItem("Feedback #${it.id}",it.message.orEmpty(),listOfNotNull(it.expectedLabel,it.feedbackText).joinToString(" • "),it.createdAt.replace('T',' ').take(19))})}catch(_:Exception){show(emptyList())}}}
}
