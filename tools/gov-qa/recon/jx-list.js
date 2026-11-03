
var codeNameArr = window.codeName ? [codeName] : [];
var listParam = {
  channelCode: [codeName],
  pageSize: 15,
		sort:"sortNum",
		order:"desc"
}
if(channelsTagSelf.aggregationChannel == '1'){
  channelId = channelsTagSelf.aggChannelIds;
  channelId = channelId.split(',') //格式转换
  listParam = {
    channelCode: [],
    webSiteCode:[],//修复外站聚合问题260331
    channelId: channelId,
    pageSize: 15,
		sort:"sortNum",
		order:"desc"
  }
}
$(function () {
  // 省政府会议 显示所有子栏目信息
  if(codeNameArr == 'zfhy'){
    listParam = {
        channelId: ['1750738143116713984','1750738143947186176','1750738144911876096'],
        pageSize: 15,
        webSiteCode:[]
      }
  }
  // 空气质量预报 生活饮用水源监测信息 跨站聚合信息取消站点代号
  if(codeName == 'kqzly'||codeName == 'shyys'){
      listParam = {
        channelId: channelId,
        pageSize: 15,
        webSiteCode:[],
        sort:"sortNum",
        order:"desc"
      }
  }
  
  // list.html分页列表
  if ($('#data-articleList').length > 0) {
    commonApi.getQueryList(listParam, null, {
        listDom: '#data-articleList',
        pageDom: '.pagination',
        isContent: false, //是否取正文
        createHtml: function (itemObj) {
          var _title = itemObj.title;
             var className = '';
            
          if (window.codeName == 'zfgzb') {
            var LinkTitle = '';
            if (itemObj.metadata) {
              LinkTitle = JSON.parse(itemObj.metadata).LinkTitle
            }
            if (LinkTitle) {
              _title = LinkTitle
            }
          }
          if (window.codeName == 'sjfb') {
              var _sjfbmetadata = JSON.parse(itemObj.metadata)
              console.log(_sjfbmetadata.sjxz)
                $('.page-infolist').addClass('sjfbinfolst')
                 if (_sjfbmetadata.sjxz === '折线图') {
                        className = 'icon zxt';
                    } else if (_sjfbmetadata.sjxz === '柱状图') {
                        className = 'icon zzt';
                    } else if (_sjfbmetadata.sjxz === '饼状图') {
                        className = 'icon bzt';
                    }
              
          }
          if(window.codeName == 'jrgz' || window.codeName == 'jxyw' || window.codeName == 'tt'){
            _title = commonApi.extractContentFromPTag(itemObj.showTitle) || itemObj.title;
          }
          return '<li class="'+className+'">\
                    <i></i>\
                    <a target="_blank" title="' + _title + '" href="' + itemObj._url + '">' + _title + '</a>\
                    <span class="time">' + itemObj.pubDate.substring(0, 10) + '</span>\
                </li>';
        }
      });
  }
  if ($('#data-articleList-notime').length > 0) {
    commonApi.getQueryList(listParam, null, {
      listDom: '#data-articleList-notime',
      pageDom: '.pagination',
      isContent: false, //是否取正文
      createHtml: function (itemObj) {
        var _title = itemObj.title;
        if (window.codeName == 'zfgzb') {
          var LinkTitle = '';
          if (itemObj.metadata) {
            LinkTitle = JSON.parse(itemObj.metadata).LinkTitle
          }
          if (LinkTitle) {
            _title = LinkTitle
          }
        }
        return '<li>\
                  <a class="box" target="_blank" title="' + _title + '" href="' + itemObj._url + '">' + _title + '</a>\
              </li>';
      }
    });
  }

  // list_pic.html分页列表
  if ($('#data-picList').length > 0) {
    commonApi.getQueryList(listParam, null, {
      listDom: '#data-picList',
      pageDom: '.pagination',
      isContent: false, //是否取正文
      createHtml: function (itemObj) {
        return '<li>\
                  <a class="box" href="' + itemObj._url + '" target="_blank"  title="' + itemObj.title + '">\
                    <div class="imgratio">\
                      <div class="imgratio-imgbox">\
                        <img class="imgratio-img" src ="' + itemObj._images.cover + '"  alt="' + itemObj.title + '" />\
                      </div>\
                    </div>\
                    <div class="txt elli-s">' + itemObj.title + '</div>\
                  </a>\
                </li>';
      }
    });
  }

  // 设置归档水印
  commonApi.setGdWatermark(channelsTagSelf, channelsTagParent, function (gdDate) {
    $('.page-mainbox').append('<div class="gd-watermark"><img src="/default/common/images/guidang.png"><span class="date">归档日期：<b>' + gdDate + '</b></span></div>');
  })

  // 设置归档水印
  commonApi.setGdWatermark(channelsTagSelf, channelsTagParent, function (gdDate) {
    $('.ztpage-mainbox').append('<div class="gd-watermark"><img src="/jxsrmzf/pc2024/images/index/jxguidang.png"><span class="date">归档日期：<b>' + gdDate + '</b></span></div>');
  })
  //lists.html 聚合列表
  if ($('#data-lists').length > 0) {
    commonApi.getArticleLists(channelsTagSelf, '#data-lists', 5, function (item) {
      return '<div class="tab-brief mb30">\
              <div class="hd mark clearfix mb10 line">\
                <ul class="clearfix">\
                  <li class="on"><a href="' + item._url + '">' + item.name +'</a></li>\
                </ul>\
                <span class="more com-more">\
                  <a href="' + item._url + '">更多 ></a>\
                </span>\
              </div>\
              <div class="bd clear">\
                <div class="item">\
                  <ul class="infolist md res dot" id="data-channel-' + item.code + '"></ul>\
                  <div class="m-com-more mt20">\
                      <a href="' + item._url + '">更多 +</a>\
                  </div>\
                </div>\
              </div>\
            </div>';
    }, function (item) {
      return '<li><a href="' + item._url + '" target="_blank" title="' + item.title + '">' + item.title + '</a><span class="time">' + item._time.yyyyMMdd + '</span></li>';
    })
  }

  // list_channel.html 子栏目列表
  if ($('#data-channelList').length > 0) {
    commonApi.getChannelsNav(channelsTagSelf, '#data-channelList', '', function (item) {
      return '<li><a target="_blank" title="' + item.name + '" href="' + commonApi.editData.getUrl(item) + '"><span>' + item.name + '</span></a></li>';
    })
  }

  // interview_list.html分页列表
  if ($('#interview-data-list').length > 0) {
    listParam = {
        channelCode: [codeName],
       pageSize: $("#pageSize").val() || 9
    }
    commonApi.getQueryList(listParam, null, {
      listDom: '#interview-data-list',
      pageDom: '.pagination',
      isContent: false, //是否取正文
      createHtml: function (itemObj) {
        return '<li>\
                  <div class="box">\
                    <div class="imgratio">\
                      <a class="imgratio-imgbox" href="' + itemObj._url + '" target="_blank"  title="' + itemObj.title + '">\
                        <img class="imgratio-img" src ="' + itemObj._images.cover + '"  alt="' + itemObj.title + '" />\
                      </a>\
                    </div>\
                    <div class="txt">\
                      <h4 class="elli-m">\
                        <a  href="' + itemObj._url + '" target="_blank"  title="' + itemObj.title + '">' + itemObj.title + '</a>\
                      </h4>\
                      <span class="time">' + itemObj._time.yyyyMMdd + '</span>\
                    </div>\
                  </div>\
                </li>';
      }
    });
  }

});