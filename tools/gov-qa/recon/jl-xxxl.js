/**
 * 18.8.23 yxl
 * 问政信箱详情
 */

// 
$(document).ready(function () {

    // 概览传来的id
    var govmsgboxId;
    var link = window.location.href;

    var firLink = link.split("id=");
    var twoLink = firLink[1].split("&");
    var govmsgboxId = twoLink[0];
    // 站点siteId（其实也是必传）
    if (link.indexOf("siteId") > 0) {
        var firSiteId = link.split("siteId=");
        var twoSiteId = firSiteId[1].split("&");
        var siteId = twoSiteId[0];
    }

    // 页面加载时加载验证码
    var contextPath = "https://haiyun.jl.gov.cn/IGI"; //全局变量，路径地址
    // var EsiteId = govmsgboxId;//全局变量（站点）
    var EsiteId = siteId ? siteId : 639;
 
	var blStatusHtml=''
    $.ajax({
        type: "GET",
        url: contextPath + "/nbhd/openGovmsgbox.do?method=viewGovmsgbox&siteId=" + EsiteId + "&metadataId=" + govmsgboxId,
        dataType: "json",
        success: function (data) {
            if (data.datas) {
                  //处理回复情况
        if (data.datas.STATUS == '7') {
			blStatusHtml = '<span class="huifu">\u5df2\u529e\u7ed3</span>'
          //  $(".huifu").text('\u5df2\u529e\u7ed3');
        } else {
			blStatusHtml = '<span class="huifu">\u529e\u7406\u4e2d</span>'
            //$(".huifu").text('\u529e\u7406\u4e2d');
        }
         $('.lyxq_box').html('')
        //处理来信情况
		$('.lyxq_box').append('<div class="liuyan_list_top commont_box "><span class="zx_title">' + data.datas.TITLE + '</span><span class="zixun">' + data.datas.GOVMSGBOXTYPE + '</span>'+blStatusHtml+'</div><div class="liuyan_list_bottom"><span class="name">' + data.datas.USERNAME + '</span><span class="time">' + $.myTime.UnixToDate(data.datas.SUBMITTIME, false) + '</span></div><div class="liuyan_list_middle">' + data.datas.CONTENT + '</div>');
 
             $('title').html(data.datas.TITLE) 
        //处理办理结果

        // 内容拼接
        var cloneArr = [];
					var num = data.datas.REPLYS.length -1;
				 if ( typeof data.datas.REPLYS[num].ATTACHLIST[0] != "undefined"){
  var APPENDIXID =data.datas.REPLYS[num].ATTACHLIST[0].APPENDIXID;
   var FILENAME = data.datas.REPLYS[num].ATTACHLIST[0].FILENAME ;
var FILEPATH ="https://haiyun.jl.gov.cn/IGI/nbhd/openGovmsgbox.do?method=readFileWithAuthorization&appendixId="+APPENDIXID + "&govmsgboxId=" + govmsgboxId;
}else {
FILEPATH ='';
FILENAME  ='';
};
					 var str ="<div class='replay_box_l'>" +
						   "<img src='../../../../images/tj_ico_20211014.png' />" +
						   "<label>" + data.datas.REPLYS[num].REPLYDEPTEXTNAME + "</label>" +
						   "</div>" +
						   "<div class='replay_box_r'>" +
						   "<div class='hf'>" +
                           "<h3>\u60a8\u597d\uff1a</h3>" +
                           "<p>" + data.datas.REPLYS[num].REPLYCONTENT + "</p>" +
						 "<p><a href="+ FILEPATH+" >" + FILENAME  + "</a></p>" +
						   "</div>" +
						   "<div class='time1'>" + $.myTime.UnixToDate(data.datas.REPLYS[num].REPLYTIME, false) + "</div>" +
						   "</div>";
            cloneArr.push(str);
       
        for (var j = 0; j < cloneArr.length; j++) {
            $(".replay_box").append(cloneArr[j]);
        }

		// 评价情况
		var scoreValue = "";
		if (data.datas.SCORE == 0 || data.datas.SCORE == null || data.datas.SCORE == "" || data.datas.SCORE == undefined ) {
			scoreValue = "\u6682\u65e0\u8bc4\u4ef7";
			
		}else  if (data.datas.SCORE == 1) {
			scoreValue = "\u4e0d\u6ee1\u610f";
			$(".Star1 label").removeClass('cs');
                    $(".Star1 label").eq(0).addClass('cs');
                   $(".Star1 label").eq(0).prevAll().addClass('cs');
		} else if (data.datas.SCORE == 2) {
			scoreValue = "\u4e00\u822c";
			$(".Star1 label").removeClass('cs');
                    $(".Star1 label").eq(1).addClass('cs');
                   $(".Star1 label").eq(1).prevAll().addClass('cs');
		} else if (data.datas.SCORE == 3) {
			scoreValue = "\u57fa\u672c\u6ee1\u610f";
			$(".Star1 label").removeClass('cs');
                    $(".Star1 label").eq(2).addClass('cs');
                   $(".Star1 label").eq(2).prevAll().addClass('cs');
		} else if (data.datas.SCORE == 4) {
			scoreValue = "\u6ee1\u610f";
			$(".Star1 label").removeClass('cs');
                     $(".Star1 label").eq(3).addClass('cs');
                     $(".Star1 label").eq(3).prevAll().addClass('cs'); 
		} else if (data.datas.SCORE == 5) {
			scoreValue = "\u975e\u5e38\u6ee1\u610f";
			 $(".Star1").find("label").addClass('cs');
		}
		$(".pjzs").html(scoreValue);
            } else {
                $(".inner-ct-ajax").empty();
            }

        },
        error: function (a, b, c) {
                alert("\u7cfb\u7edf\u9519\u8bef\uff0c\u8bf7\u8054\u7cfb\u7f51\u7ad9\u7ba1\u7406\u4eba\u5458");
               
            }
    });
    

	
	
	
});