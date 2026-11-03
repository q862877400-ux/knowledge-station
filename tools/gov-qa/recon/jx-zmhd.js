$(function () {
  //我向省长建言
  commonApi.addArticleList(zmhdData.articleLists.wxszj, {
    pageSize: 6
  }, {
    listDom: '#zmhd-data-wxszj',
    createHtml: function (item) {
      return '<li>\
                <div class="box">\
                  <div class="tit elli-m"><a target="_blank" title="' + item.title + '" href="' + item._url + '">' + item.title + '</a></div>\
                  <span class="time">发布时间：' + item.pubDate + '</span>\
                </div>\
              </li>';
    },
  });

  //在线访谈
  commonApi.getQueryList({
    current: 1,
    pageSize: 3,
    channelCode: ['zxft'],
    webSiteCode: [websiteCode],
    havePictures: true
  }, null, {
    listDom: '#zmhd-data-zxft',
    createHtml: function (item) {
      console.log(item)
      var _title = item.title;
      var _url = item._url;
      return '<li>\
                <div class="box">\
                  <div class="pic imgscale">\
                    <div class="imgratio">\
                      <a class="imgratio-imgbox" href="' + _url + '" title="' + _title + '" target="_blank">\
                        <img class="imgratio-img" src="' + item._images.cover + '" alt="' + _title + '" />\
                      </a>\
                    </div>\
                  </div>\
                  <div class="txt">\
                    <div class="tit elli-m"><a href="' + _url + '" title="' + _title + '" target="_blank">' + _title + '</a>\
                    </div>\
                    <span class="time">'+ item.pubDate +'</span>\
                  </div>\
                </div>\
              </li>';
    },
  })

  //回应关注
  commonApi.addArticleList(zmhdData.articleLists.hygz, {
    pageSize: 4
  }, {
    listDom: '#zmhd-data-hygz',
    createHtml: createHtmlFn.infolist,
  });

  
getCollectList('#zmhd-data-dczj',3)

//民意征集 显示包括部门的征集
function getCollectList(dom, pagesize) {
	$.get(ajaxUrl.sr.hd.collect.list, {
		tenantId: defaultConfig.userIdObj.tenantId,
		// siteId: defaultConfig.userIdObj[websiteCode].qdId,
    siteId:collect_siteIds,
    //deptId:deptIdArr,
    openFlag:1,
		//sort: 'startTime',
		sort: 'endTime',
		order: 'desc',
		current: 1,
		pagesize: pagesize,
    collectStatus: '602,603'
	}).done(function(res) {
		var list = res.data;
		if(list && list.length > 0) {
			var _li = '';
			$.each(res.data, function(index, itemObj) {
				var id = itemObj.id
				var text = itemObj.title
        var statusText=(itemObj.longTimeOpinion == 1)?'进行中': defaultConfig.statusCode[itemObj.collectStatus]
				var star = itemObj.startTime
				var end =(itemObj.longTimeOpinion == 1)?'长期': itemObj.endTime
        var linkUrl =(itemObj.outJoinUrl != '')? itemObj.outJoinUrl:'/' + websiteCode + '/collect/detail.html?id=' + id
				var statusClass = statusText == '已结束' ? 'over' : 'ing';
        //var _url = statusText === '已结束' ? (linkUrl + '&type=1') : linkUrl;
				var _url = linkUrl;
       _li += '<li class="' + statusClass + '">\
                <div class="box">\
                  <div class="status"><span>' + statusText + '</span></div>\
                  <div class="txt">\
                    <div class="tit elli-s"><a target="_blank" title="' + text + '" href="' + _url + '">' + text + '</a></div>\
                    <div class="time">征集时间：' + star.substring(0,10)+'  截至时间：'+ end.substring(0,10) +'</div>\
                  </div>\
                </div>\
              </li>';
			})
			$(dom).html(_li);
		}
	})
}




});



//将字符串日期(格式：Y-m-d H:i:s )转换成日期对象
function newDateObj(time) {
  //参数日期格式：Y-m-d H:i:s
  var arr = time.split(' '),
    arr1 = arr[0].split("-"),
    arr2 = arr[1].split(":");
  arr = arr1.concat(arr2);
  // 创建一个目标日期对象
  var targetDate = new Date(arr[0], arr[1] - 1, arr[2], arr[3], arr[4], arr[5]);
  return targetDate;
}

//根据开始结束日期判断征集状态
function collectState(startDateObj, endDateObj) {
  // startDateObj:开始日期对象， endDateObj:结束日期对象
  var state = "";
  var today = new Date();
  //日期对象也可用于比较两个日期。
  if (endDateObj < startDateObj) {
    return '';
  } //开始日期大于结束日期  返回undefined

  if (today > endDateObj) {
    state = '已结束';
  } else if (today < endDateObj && today > startDateObj) {
    state = '进行中';
  } else { // 还没到开始日期
    state = '未开始';
  }
  return state;

}