/**
 * 18.8.23 yxl
 * 问政信箱详情
 */
var StartDate;
$(document).ready(function () {
    var link = window.location.href;
    var siteId;
    var appId;
    if (link.indexOf("siteId") > 0) {
        var firSrc = link.split("siteId=");
        var twoSrc = firSrc[1].split("&");
        var siteIds = null;
        var siteIds = twoSrc[0];//上一个页面传递过来的siteId
    }
    if (link.indexOf("siteid") > 0) {
        var firSrc = link.split("siteid=");
        var twoSrc = firSrc[1].split("&");
        var siteIds = null;
        var siteIds = twoSrc[0];//上一个页面传递过来的siteId
    }
    if (link.indexOf("appId") > 0) {
        var secSrc = link.split("appId=");
        var threeSrc = secSrc[1].split("&");
        var appIds = null;
        var appIds = threeSrc[0];//上一个页面传递过来的siteId
    }
    var contextPath = "https://haiyun.jl.gov.cn/IGI";
    var jumpPath = "lyxdct";//跳转页面的名称

    siteId = siteIds ? siteIds : 117;
    appId = appIds ? appIds : 96;







    // 信件列表
    var pageIndex = 1;
    var pageSize = 4;    //默认是5
    var order = 1;
	var groupId=172;
    function tableInfoPage() {
        var tabAllPage;
        $.ajax({
            type: "GET",
            url: contextPath + "/nbhd/openGovmsgbox.do?method=listGovmsgboxs&siteId=" + siteId + "&order=" + order + "&appId=" + appId + "&pageIndex=" + pageIndex + "&pageSize=" + pageSize+ "&groupId=" + groupId,
            async: false,//同步
            dataType: "json",
			
            success: function (data) {
				 if (data.statusCode == 200) {
						$('.BJTJ').append('<li><div class="icoBox"><img src="/images/tj_ico2_20200303.png" /></div><div class="text"><label>公开件</label><span>' + data.datas.pageInfo.totalResults + '</span></div></li>');
                }

                if (data.datas.data) {
                    attrsTable(data);
                    tabAllPage = data
                } else {
                    $(".liuyan_list ul").empty();
                    $(".liuyan_list ul").append("<li>暂无数据...</li>")
                }

            },
           
        });
        return tabAllPage
    }

    function attrsTable(data) {
        $(".liuyan_list ul").empty();
        // 表头
     
        var cloneArr = [];
        var status = "";
        for (var i = 0; i < data.datas.data.length; i++) {
            if (data.datas.data[i].STATUS  == '7') {
                status = "已办结"
            } else {
                status = "处理中"
            }
			   var www=window.screen.width;
			 var hdnr = data.datas.data[i].CONTENT;
			 var hdnr_length = hdnr.length;
		   console.log(hdnr_length );
		   if(hdnr_length > 107){
			   hdnr = hdnr.substring(0,107)+"..."
		   }
			if(www<=450){
				 if(hdnr_length > 80){
	                  hdnr = hdnr.substring(0,30)+"...";
				 }
	        }
			
 var str = "<li>" +
			  "<a target='_blank' href='/zmhd/tzxx/" + jumpPath + ".html?id=" + data.datas.data[i].METADATAID + "&siteId=" + siteId + "'>" +
			"<div class='liuyan_list_top'>" +
			"<span class='zx_title'>" + data.datas.data[i].TITLE  +"</span>" +
			"<label class='zixun'>" + data.datas.data[i].GOVMSGBOXTYPE + "</label>" +
			"<label class='huifu'>" + status + "</label>" +
			"</div>" +
			"<div class='liuyan_list_middle'>" +
			"<span class='liuyan_content'>" + hdnr + "</span>" +
			"</div>" +
			"<div class='liuyan_list_bottom'>" +
			"<span class='name'>" + data.datas.data[i].USERNAME + "</span>" +
			"<span class='time'>" + $.myTime.UnixToDate(data.datas.data[i].SUBMITTIME, false) + "</span>" +
			"</div>" +
			"</a>" +
			"</li>";

			

            cloneArr.push(str);
        }
        for (var j = 0; j < cloneArr.length; j++) {
            $(".liuyan_list ul").append(cloneArr[j]);
        }

    }

    var tabAllPages = tableInfoPage();
    if (tabAllPages) {
        var tabTotalPage = tabAllPages.datas.pageInfo.totalPages ? tabAllPages.datas.pageInfo.totalPages : 0;
        var setTotalCount = tabAllPages.datas.pageInfo.totalResults ? tabAllPages.datas.pageInfo.totalResults : 0;
    } else {
        var tabTotalPage = 1;
        var setTotalCount = 1
    }

	
	// 统计
	tongji();
	function tongji() {
        $.ajax({
            type: "GET",
            url: contextPath + "/nbhd/openGovmsgbox.do?method=countGovmsgboxs&siteId="+siteId+"&appId="+appId+ "&deptIds=" + groupId,
            async: false,
            dataType: "json",
			/*data:{
                     beginTime:StartDate,//信件标题
	                 endTime:EndDate,//信件内容
					 },*/
            success: function (data) {
                if (data.statusCode == 200) {
						$('.BJTJ').append('<li><div class="icoBox"><img src="/images/tj_ico1_20200303.png" /></div><div class="text"><label>共接收</label><span>' + data.datas.totalCount + '</span></div></li><li><div class="icoBox"><img src="/images/tj_ico_20200303.png" /></div><div class="text"><label>已办结</label><span>' + data.datas.finishCount + '</span></div></li>');
                }
            },
            error: function (a, b, c) {
                           alert("系统错误，请联系网站管理人员");
                           return;
                       }
        });
	}
})





























