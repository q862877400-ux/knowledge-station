'use strict';

var cName = '';
var code = $('meta[name=code]').attr('content');
var channelId = $('meta[name=channelId]').attr('content');
var ispiclist = $('.piclist').length > 0;

(function () {

	var listLi = $('#list li'),
	    num = parseInt($("#pageSize").val());
		console.log(listLi.length)
	if (listLi.length < num + 1) {
		$('.columnMore').hide();
	} else {
		listLi.eq(num).hide();
		$('.columnMore').click(function () {
			$(this).hide();
			$("#page_div").bindEvent({});
			table_ajax();
		});
	}
	// 图片损坏替换默认图片
	$(".piclist img.img").each(function(){
		var _src = $(this).attr('src');
		if(_src == '' || _src == '/null'){
			$(this).attr('src','/hlj/xhtml/images/zwgk/tb_default.png'); //替换损坏的图片
		}
	})
})();

function GetQueryString(name) {
	var reg = new RegExp('(^|&)' + name + '=([^&]*)(&|$)');
	var r = window.location.search.substr(1).match(reg);
	if (r != null) return decodeURI(r[2]);
	return null;
}

function table_page(totalHits) {
	var totalHits = parseInt(totalHits);

	var pageSize = parseInt($("#pageSize").val());
	var page = parseInt($("#page").val());
	var pageNum = Math.floor((totalHits + pageSize - 1) / pageSize);

	var options = {
		pageNum: pageNum,
		current: page,
		backfun: function backfun(e) {
			$("#page").val(e.current);
			table_ajax();
		}
	};

	$("#page_div").createPage(options);
}

function table_ajax() {
	$.ajax({
		url: '/common/search/' + channelId + '?_isAgg=false&_isJson=true&_pageSize=' + parseInt($("#pageSize").val()) + '&_template=index&_rangeTimeGte=&_channelName=&page=' + parseInt($("#page").val()) + '',
		type: 'get',
		async: false,
		success: function success(data) {

			table_page(data.data.total);
			table_each("list", data.data.results);
		},
		error: function error(err) {
			console.log(err);
		}
	});
}

function ajax_success(json) {
	var list = [];
	var resutList = json.data.results;
	$.each(resutList, function (name, val) {
		var myValues = val;
		var json = {
			"title": myValues.title,
			"url": myValues.url,
			"publishedTimeStr": val.publishedTimeStr
		};
		if (ispiclist) {
			json.imgsrc = val.resList.length > 0 ? val.resList[0].filePath : '';
		}
		list.push(json);
	});
	return list;
}

function table_each(id, json) {
	var tab = $("#" + id);
	tab.empty();
	var _li = '';
	var windowWidth = $(window).width();

	$.each(json, function(i, v){
		//临时处理 关于黑龙江省冰雪节的建议 回复内容
		var _str = '网民朋友，您的留言收悉，已交由相关部门研究参考。感谢您的宝贵建议，祝您身体健康，生活愉快！';
		var _val = v.manuscriptId == '31790436' ? _str : (v.domainMetaList[0].resultList.length > 0 ? v.domainMetaList[0].resultList[7].value : '')
			_li += '<li>\
						<div class="lititle"><h3><a href="' + v.url + '" target="_blank">' + v.title + '</a></h3>\
						<font>' + (v.domainMetaList[0].resultList.length > 0 ? v.domainMetaList[0].resultList[5].value : '') + '</font>\
						<a class="btn">' + (v.domainMetaList[0].resultList.length > 0 ?v.domainMetaList[0].resultList[10].value : '') + '</a>\
						<a class="' + (v.domainMetaList[0].resultList.length > 0 && v.domainMetaList[0].resultList[3].value ? "btn" : "btnhide") + '">' + (v.domainMetaList[0].resultList.length && v.domainMetaList[0].resultList[3].value ? v.domainMetaList[0].resultList[3].value : " ") + '</a>\
						<span><b>回复时间： </b>' + (v.domainMetaList[0].resultList.length > 0 ?v.domainMetaList[0].resultList[4].value.substr(0, 10): '') + '</span></div>\
						<div class="hf"><strong tabindex="0">'+(v.domainMetaList[0].resultList.length > 0 ? v.domainMetaList[0].resultList[1].value : '') +'回复：</strong>\
						<a href="' + v.url + '" target="_blank">'+_val +'</a></div>\
						</li>';

	})

	tab.html(_li);

}
function requestParent() {
	$.ajax({
		url: '/common/getLocalList?regionCode=' + code + '',
		//url: '/common/getLocalList?regionCode=' + GetQueryString('code'),
		type: 'get',
		async: 'true',
		success: function success(data) {
			var _nav = '';
			if (data.code == '200') {
				_nav = '<p><a href="/gsszf/index.shtml">首页</a> > ';
				for (var i = 0; i < data.results.channelLevel.length; i++) {
					if (i != data.results.channelLevel.length - 1) {
						_nav += '<a href="' + data.results.channelLevel[i].url + '">' + data.results.channelLevel[i].channelName + '</a> > ';
					} else {
						_nav += '<span>' + data.results.channelLevel[i].channelName + '</span>';
					}
				}
				_nav += '</p>';
			}
			//$('#BreadcrumbNav').empty().html( _nav);
			var a = $('.BreadcrumbNav a').eq(1).html().trim();
			$(".nav a").each(function () {
				if ($(this).text() == a) {
					$(this).addClass("active").siblings().removeClass('active');
				}
			});
		},
		error: function error(err) {
			console.log(err);
		}
	});
}