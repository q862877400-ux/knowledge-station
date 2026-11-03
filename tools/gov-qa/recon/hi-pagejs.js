function createPageHTML(divName,_nPageCount, _nCurrIndex, _sPageName, _sPageExt,_nPageSum){ 
 	var head = document.getElementsByTagName('head')[0];
	var style = document.createElement("link");
	style.href = "";
	style.rel = "stylesheet";
	style.type = "text/css";

    head.insertBefore(style,head.childNodes[0]);
	
	
 
 
 var con_text = "";
  if(_nPageCount == null || _nPageCount<1){ 
   return; 
 } 
  var nCurrIndex = _nCurrIndex; 
	con_text += "<div class=\"pagination_index\" >";
  
   if(_nPageCount>1)
   	con_text +="<span class=\"arrow\"><a href=\""+_sPageName+"."+_sPageExt+"\">首页</a></span></div> ";
  else
  	con_text +="<span class=\"arrow\">首页</span></div> ";
	
  if(nCurrIndex>1){
    if((nCurrIndex-1)>0){
    	if((nCurrIndex-1)==1)
    		con_text += "<div class=\"pagination_index\"><span class=\"arrow\"><a href=\""+_sPageName+"."+_sPageExt+"\">上一页</a></span></div>";
  	  	else
  	  		con_text += "<div class=\"pagination_index\" ><span class=\"arrow\"><a href=\""+_sPageName+"_" + (nCurrIndex-1) +"."+_sPageExt+"\">上一页</a></span></div>";
  	  } 
  }
  var startpage=0,endpage =0;
  if(nCurrIndex > 5){
  	  startpage = nCurrIndex-2;
  	if(_nPageCount-nCurrIndex>2){
  		endpage =nCurrIndex+2;
  	}else{
  		endpage = _nPageCount;
  	}
  }else if(_nPageCount<6){
  	  startpage = 1;
      endpage = _nPageCount;
  }else{
  	  startpage = 1;
  	  endpage = 6;
  }

  for(var k=startpage; k<=endpage; k++){
     var param = "";
     if(k >1 ) param = "_" + k;
  	if(k==nCurrIndex)
  	   con_text += "<div class=\"pagination_index_num currentIndex\">"+k+"</div>";
  	else
  	   con_text += "<div class=\"pagination_index_num\"><a href=\""+_sPageName+param + "."+_sPageExt+"\">"+k+"</a></div>";
  }
 if(nCurrIndex<_nPageCount){
 	con_text += "<div class=\"pagination_index\"><span class=\"arrow\"><a href=\""+_sPageName+"_" + (nCurrIndex+1) + "."+_sPageExt+"\">下一页</a></span></div>";
 }
 
 con_text += "<div class=\"pagination_index\"> <span class=\"arrow\">"; 
 
 if(_nPageCount>1)
 con_text += "<span class=\"arrow\"><a href=\""+_sPageName+"_" + (_nPageCount) + "."+_sPageExt+"\">末页</a></span>"; 
 else
 con_text += "<span class=\"arrow\">末页</span>"; 
 
 con_text += "</div>";
 
 
 
 
 con_text += "</div> <div class=\"pagination_index_last\">第 "+nCurrIndex+" 页 转<input name='pagination_input' id='pagination_input' />页 <a href='#' onclick=\"pagination_go('"+_sPageName+"','"+_sPageExt+"','"+_nPageCount+"')\" >GO</a>  共 "+_nPageSum+" 条 共 "+_nPageCount+" 页</div>";
 if("undefined" != typeof channelId){ 
 	if(channelId=='55acf8539596d25624059980986aaa78'||channelId=='383e30595d574a01aae4ee8f5cac8386'||channelId=='2f11247a5c2c49eeb3cdbb00a8178bc7'){
		con_text = "<div style=\"width: 111px;height: 28px;font-size: 14px;color: #666666;background: #dcdcdd;display: block;margin: 0 auto;line-height: 28px; text-align: center;\"><a target=\"_blank\" href=\"/common/search/"+channelId+"?_isAgg=false&_pageSize="+pagesize+"&_template="+_template+"&_channelName=&page=1\">更多>></a></div>";  
	}
    if(channelId=='82cdb5b25e514a1bba6429aef621ce6c'){
		con_text = "<div style=\"width: 111px;height: 28px;font-size: 14px;color: #666666;background: #dcdcdd;display: block;margin: 0 auto;line-height: 28px; text-align: center;\"><a target=\"_blank\" href=\"/common/search/"+channelId+"?_isAgg=false&_pageSize="+pagesize+"&_template="+_template+"&sort=publishedTime&_channelName=&page=1\">更多>></a></div>";  
	}
	/* if (_nPageSum==500&&_nPageCount==_nCurrIndex){
		con_text += "<div class=\"pagination_index\"><span class=\"arrow\"><a target=\"_blank\" href=\"/common/search/"+channelId+"?_isAgg=false&_pageSize="+pagesize+"&_template="+_template+"&_channelName=&page="+(_nPageCount)+"\">更多</a></span>";  
	 }*/
 }
 document.getElementById(divName).innerHTML = con_text;
 //setTableInnerHTML(document.getElementById(divName),con_text)
//$("#"+divName).html(con_text);
} 


function setTableInnerHTML(table, html) {
   if(navigator&&navigator.userAgent.match(/msie/i)){
      var temp = table.ownerDocument.createElement('div');
      temp.innerHTML = '<table><tbody>' + html + '</tbody></table>';
      if(table.tBodies.length == 0){
         var tbody=document.createElement("tbody");
         table.appendChild(tbody);
      }
      table.replaceChild(temp.firstChild.firstChild, table.tBodies[0]);
   }else{
      table.innerHTML=html;
   }
}
function pagination_go(sPageName,sPageExt,nPageCount){
	var gopageID = document.getElementById('pagination_input').value;
	gopageID= gopageID.replace(" ",'');
	if(gopageID){
		if(parseInt(gopageID)<=nPageCount && parseInt(gopageID)>0){
			if(gopageID=="1"){
				window.location.href = sPageName+"."+sPageExt;
			}else{
				window.location.href = sPageName+"_" + gopageID + "."+sPageExt;
			}
		}
	}
	return false;
}