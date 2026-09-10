package com.kriss.smsshield.adapter
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.kriss.smsshield.databinding.ItemCommunityBinding
data class CommunityDisplayItem(val title:String,val message:String,val detail:String,val date:String)
class CommunityAdapter(private var items:List<CommunityDisplayItem>):RecyclerView.Adapter<CommunityAdapter.Holder>(){
 class Holder(val b:ItemCommunityBinding):RecyclerView.ViewHolder(b.root)
 override fun onCreateViewHolder(p:ViewGroup,v:Int)=Holder(ItemCommunityBinding.inflate(LayoutInflater.from(p.context),p,false))
 override fun getItemCount()=items.size
 override fun onBindViewHolder(h:Holder,p:Int){val x=items[p];h.b.titleText.text=x.title;h.b.messageText.text=x.message;h.b.detailText.text=x.detail;h.b.dateText.text=x.date}
 fun submit(value:List<CommunityDisplayItem>){items=value;notifyDataSetChanged()}
}
