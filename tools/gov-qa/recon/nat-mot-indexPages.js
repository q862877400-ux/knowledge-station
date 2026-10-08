function frontGeneratorPage(pageNo,pages,pageids){
	 if(isPc){
		 	var pagestr ="<ul class=\"pagination pagination-center\" style=\"margin-top: 14px;\">";
		    if(pageNo > 1){
		        pagestr += '  <li>  <a href="javascript:;" aria-label="Previous" onclick="toPrev('+pageNo+');"><span aria-hidden="true">&laquo;</span> </a> </li>';
		    }else{
		        pagestr += '  <li>  <span aria-hidden="true">&laquo;</span></li>';
		    }
		    //中间页码
		    if(pageNo != 1 && pageNo >= 4 && pages != 4){
		        pagestr += '<li> <a href="javascript:;" onclick="toPage('+1+');">'+1+'</a></li>';
		    }
		    if(pageNo-2 > 2 && pageNo <= pages && pages > 5){
		        pagestr += '<li><span>...</span></li>';
		    }
		    var start = pageNo -2,end = pageNo+2;
		    if((start > 1 && pageNo < 4)||pageNo == 1){
		        end++;
		    }
		    if(pageNo > pages-4 && pageNo >= pages){
		        start--;
		    }
		    for (;start <= end; start++) {
		        if(start <= pages && start >= 1){
		            if(start != pageNo){
		                pagestr += '<li><a href="javascript:;" onclick="toPage('+start+');">'+ start +'</a></li>';
		            }else{
		                pagestr += '<li  class="active"><span style="    background: lightgray;"><a href="javascript:void(0);return false;">'+ start +'<a/></span></li>';
		            }
		        }
		    }
		    if(pageNo + 2 < pages - 1 && pageNo >= 1 && pages > 5){
		        pagestr += '<li><span>...</span></li>';
		    }
		    if(pageNo != pages && pageNo < pages -2  && pages != 4){
		        pagestr += '<li><a href="javascript:;" onclick="toPage('+pages+');">'+pages+'</a></li>';
		    }
		    //下一页
		    if(pageNo < pages){
		        pagestr += '<li><a href="javascript:;"  onclick="toNext('+pageNo+');">&raquo;</a></li>';
		    }else{
		        pagestr += '<li><span>>></span></li>';
		    }
		    pagestr += ' <li class="page_tz">'+
					    ' <span>跳转至第<input type="text" style="width: 30px;height: 20px;" value="1" id="fowrwardPage">页</span>'+
					    ' </li>'+
					    ' <li class="page_tz"><a href="javascript:;" onclick="fowrwardPage('+pages+')">>></a></li>';
		    pagestr += "</ul>";
		    $("#"+pageids).html(pagestr);
	 }else{
		 var pagestr ="<ul class=\"pagination pagination-center\" style=\"margin-top: 14px;\">";
		    if(pageNo > 1){
		        pagestr += '  <li>  <a href="javascript:;" aria-label="Previous" onclick="toPrev('+pageNo+');"><span aria-hidden="true">上一页</span> </a> </li>';
		    }else{
		        pagestr += '  <li>  <span aria-hidden="true">上一页</span></li>';
		    }
		    
		    //下一页
		    if(pageNo < pages){
		        pagestr += '<li><a href="javascript:;"  onclick="toNext('+pageNo+');">下一页</a></li>';
		    }else{
		        pagestr += '<li><span>下一页</span></li>';
		    }
		    $("#"+pageids).html(pagestr);
	 }
   
}

function toPrev(pageNo){
	var prev = pageNo-1;
	showAllByPage(prev);
}


function toPage(toPageNo){
	showAllByPage(toPageNo);
}

function toNext(toPageNo){
	var nextpage = toPageNo+1;
	showAllByPage(nextpage);
}

function toList(obj){
	pageSize = $(obj).val();
	showAllByPage(1);
}

function fowrwardPage(pageAll){
	var for_page = $("#fowrwardPage").val();
	var s = isNum(for_page);
	if(s){
		if(for_page > pageAll){
			for_page = pageAll;
		}
		if(for_page <= 0){
			for_page = 1;
		}
		showAllByPage(for_page);
	}else{
		swal("输入页码错误，请重新输入...");
		 $("#fowrwardPage").val('');
	}
}
/***********  验证是否为数字 -start *************/
function isNum(str){
	var r=/^[0-9]*$/; 
	return r.test(str);
 }
/***********  验证是否为数字 -end   *************/