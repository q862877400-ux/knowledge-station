
var pageIndex = 0;
var pageSize = 10;
var subject = "";
var postName = "";
var replyContent = "";
var content = "";
var startTime = "";
var endTime = "";
var group = "";

(function(win, $) {
	BindGrid(subject, postName, replyContent, content,startTime,endTime,group, pageIndex, pageSize);
	
	
	$("#ewb-sea-btn").on('click', function() {
    	var itemname = $("#gomsg").val();
		//console.log(itemname);
		var pattern = new RegExp("[%!@#$^*()=|{}':;',\\[\\].<>/~！@#￥……*（）;—|{}【】‘；：”“'。，、&]");
		if ( pattern.test(itemname.trim()) ){
			alert("请不要在关键词中输入特殊字符！");
		}else{
			BindGrid(itemname, postName, replyContent, content,startTime,endTime,group, pageIndex, pageSize);
		}

    })


	$("#ewb-cxm-btn").on('click', function() {
    	var itemname = $("#gocxm").val();
		//console.log(itemname);
		var pattern = new RegExp("[%!@#$^*()=|{}':;',\\[\\].<>/~！@#￥……*（）;—|{}【】‘；：”“'。，、&]");
		if ( pattern.test(itemname.trim()) ){
			alert("查询码有误，请重新输入");
		}else{
			searchcxm(itemname, postName, replyContent, content,startTime,endTime,group, pageIndex, pageSize);
		}

    })



	function BindGrid(subject, postName, replyContent, content,startTime,endTime,group, pageIndex, pageSize) {
		webbuilder.getLetterListByCondition(subject, postName, replyContent, content,startTime,endTime,group, pageIndex, pageSize, function (msg) {
	        $.each(msg.data, function(i,item) {
			   item.vname =  siteInfo.vname;
			});
			console.log(msg);
	        var html = Mustache.render($('#resultlist-tmpl').html(), { items: msg.data});
	        $("#letterList").empty().html(html);
	    	renderPager(subject, postName, replyContent, content,startTime,endTime,group, pageIndex, pageSize, msg.total);
	   })
	}

		function searchcxm(cxm, postName, replyContent, content,startTime,endTime,group, pageIndex, pageSize) {
	var str = {"siteGuid": siteInfo.siteGuid,"cxm": cxm,"postName":postName,"replyContent":replyContent,"content": content,"startTime":startTime,"endTime":endTime,"group": group,"pageIndex":pageIndex,"pageSize":pageSize};
		Util.ajax({
								url: siteInfo.projectName + "/rest/frontAppNotNeedLoginAction/getLetterListBycxm",
								data: str,
								success: function(msg) {
									console.log(msg)
									var msg=msg.custom;
									if (msg != null && msg != "") {
										if (msg.hasOwnProperty("message")) {
											alert(msg.message);
										}
									}
		 var html = Mustache.render($('#resultlist-tmpl').html(), { items: msg.data});
	        $("#letterList").empty().html(html);
	    	renderPager(subject, postName, replyContent, content,startTime,endTime,group, pageIndex, pageSize, msg.total);
								}
			
							}, true);
	}
	
	// 插件分页
    var $pager = $(".ewb-page2"),
        renderPager = function(subject, postName, replyContent, content,startTime,endTime,group, pageindex, pagesize, total) {
        if ($pager.pagination()) {
            $pager.pagination('destroy');
        }
        if (!total) {
            return;
        }
        var is_iPd = navigator.userAgent.match(/(iPad|iPod|iPhone)/i) !== null;
        var is_mobi = navigator.userAgent.toLowerCase().match(/(ipod|iphone|android|coolpad|mmp|smartphone|midp|wap|xoom|symbian|j2me|blackberry|win ce)/i) !== null;
        var optionPc = { //pc分页配置
                pageIndex: pageindex/pagesize,
                pageSize: pagesize,
                total: total,
                showJump: true,
                pageBtnCount: 9,
                jumpBtnText: 'Go',
                firstBtnText: '首页',
                lastBtnText: '尾页',
                showInfo: true,
                prevBtnText: '上一页',
                nextBtnText: '下一页',
                infoFormat: '共{total}条'
            },
            optionMobile = { //移动端分页配置
                pageIndex: pageindex/pagesize,
                pageSize: pagesize,
                total: total,
                pageBtnCount: 5,
                showFirstLastBtn: true,
                firstBtnText: "首页",
                lastBtnText: "尾页"
            };
        if (is_iPd || is_mobi) { //判断设备是否为pad或手机端
            $pager.pagination(optionMobile);
        } else {
            $pager.pagination(optionPc);
        }
        $pager.on("pageClicked", function(event, data) {
            //console.log(data);
        	BindGrid(subject, postName, replyContent, content,startTime,endTime,group, data.pageIndex*data.pageSize, data.pageSize);
        }).on('jumpClicked', function(event, data) {
            //console.log(data);
       		BindGrid(subject, postName, replyContent, content,startTime,endTime,group,data.pageIndex*data.pageSize, data.pageSize);
        });
    };

}(this, jQuery));





