$(function() {
	var pageIndex =1;
	var pageSum;
	var acceptLetterList;
	var totalPage;
	var url = window.location.href;
	var	regionCode;
	if(url.split("?")[1]!=undefined){
		if(url.split("&")[1]!=undefined){
			regionCode = url.split("?")[1].split("&")[1].split("=")[1];
		}else{
			regionCode = url.split("?")[1].split("=")[1];
		}
	}else{
		regionCode="650000000000";
	}
	//登陆检查
	$.ajax( {
		url : "/user/network-user-info!checkLogon.action",
		type : "post",
		async : false,
		dataType : 'html',
		data : {},
		success : function(data) {
			var user = eval('(' + data + ')');
			if (user.logonFlag != "true") {//登录后
				window.location.href = '/html/login/login.jsp?regionCode='+regionCode;
			} else {
				$.ajax( {
					url : '/letter/pre-accept-letter-info!getLetterList.action?regionCode='+regionCode,//guohua 登录哪个系统就只显示当前系统的信息
					data : {pageIndex : pageIndex,
							pageSize : 7},
					type : 'post',
					dataType : 'html',
					success : function(data) {
						var obj = jQuery.parseJSON(data);
						var letterList = obj[0].letterList;
						acceptLetterList = getAcceptLetterList(letterList);
						$("#letterlist").html(acceptLetterList);
						pageSum = obj[0].totalPage;
						var temp;
						$(".pageSum").html(pageSum);
						$(".pageIndex").html(pageIndex);
						for(var i=1;i<=pageSum;i++){
							temp += "<option value="+i+">"+i+"</option>";
						}
						$("#select").html(temp);
					},
					error : function(data) {
			
					}
				});
			}
		},
		error : function(data) {
		}
	});

	//下拉列表跳页select
	$("#select").change(function(){
		$(this).attr("selected",true);
		var val = $(this).val();
		pageIndex = val;
		$.ajax({
	    	url:'/letter/pre-accept-letter-info!getLetterList.action?regionCode='+regionCode,
	    	data:{pageIndex:pageIndex,
				  pageSize : 7},
			type:'post',
			dataType:'html',
			success:function(data){
	    		var obj = jQuery.parseJSON(data);
	    		var letterList = obj[0].letterList;
	    		totalPage = obj[0].totalPage;
				$(".pageSum").html(pageSum);
				$(".pageIndex").html(pageIndex);
				acceptLetterList = getAcceptLetterList(letterList);
			}
		});
	});
	// 首页末页跳转 第二功能模块
	$(".firstOrEnd").click(function() {
		var temp = $(this).html();
		var pi;
		if (temp == '首页') {
			pi = 1;
			pageIndex = 1;
		} else if (temp == '尾页') {
			pi = pageSum;
			pageIndex = pi;
		} else if (temp == '上一页') {
			if ((pageIndex * 1 - 1 * 1) > 0) {
				pi = pageIndex * 1 - 1 * 1;
				pageIndex = pi;
			} else {
				alert("已经到了第一页~");
				return;
			}
		} else if (temp == '下一页') {
			if ((pageIndex * 1 + 1 * 1) <= pageSum) {
				pi = pageIndex * 1 + 1 * 1;
				pageIndex = pi;
			} else {
				alert("已经在最后一页了~");
				return;
			}
		}
		$.ajax( {
			url : '/letter/pre-accept-letter-info!getLetterList.action?regionCode='+regionCode,
			data : {pageIndex : pi,
					pageSize : 7},
			type : 'post',
			dataType : 'html',
			success : function(data) {
				var obj = jQuery.parseJSON(data);
				var letterList = obj[0].letterList;
				pageSum = obj[0].totalPage;
				$(".pageSum").html(pageSum);
				$(".pageIndex").html(pi);
				acceptLetterList = getAcceptLetterList(letterList);
			},
			error : function(data) {

			}
		});
	});

});

function pageIndexList(pageSum){
	var html = "";
  	for(var i=1;i<=pageSum;i++){
    	var style;
    	if(i==1){
      		style = "style='color:red;'";
    	}
    	html+="<span class='btnA' id='btnIDA" + i +"' name='"+i+"' "+style+">"+i+"</span>";
    	style = "";
  	}
  	var  obj = $("#pageIndexList");
  	obj.html(html);
}

/**
 * 苏建东 重复代码抽出 2015年7月9日 14:44:55 增加
 */
//解析数据
function getAcceptLetterList(letterList) {
	var html="";
	html +="<tr>";
	html +="<th width='130'>提交日期</th>";
	html +="<th>内容</th>";
	html +="<th width='130'>查看详情</th>";
	html +="<th width='130'>评价</th></tr>";
	$(letterList).each(function(index,model){
        if (model.evaluationFlag =="1") {
        	html +="<tr>";
            html +="<td>"+ model.createDate+"</td>";
            html +="<td class='ellipsis'><p>"+ model.letterContent+"</p></td>";
            html +="<td class='details'><a href='../onlineInquiry/onlineInquiry.jsp?id="+model.id+"&regionCode="+regionCode+"'>查看详情</a></td>";
            html +="<td><a href='../onlineInquiry/yipinjia.jsp?petitionNo="+model.petitionNo+"&regionCode="+regionCode+"'>已评价</a></td>";
            html +="</tr>";
		}else if (model.evaluationFlag =="3") {
			html +="<tr>";
            html +="<td>"+ model.createDate+"</td>";
            html +="<td class='details'><a href='../onlineInquiry/onlineInquiry.jsp?id="+model.id+"&regionCode="+regionCode+"'>查看详情</a></td>";
            html +="<td class='ellipsis'><p>"+ model.letterContent+"</p></td>";
            html +="<td><span style='color:#888;'>超期未评价</span></td>";
            html +="</tr>";
		}else {
			html +="<tr>";
            html +="<td>"+ model.createDate+"</td>";
            html +="<td class='ellipsis'><p>"+ model.letterContent+"</p></td>";
            html +="<td class='details'><a href='../onlineInquiry/onlineInquiry.jsp?id="+model.id+"&regionCode="+regionCode+"'>查看详情</a></td>";
            html +="<td></td>";
            html +="</tr>";
		}
    	
	});
	var  obj = $("#letterlist");
	obj.html(html);
}

	