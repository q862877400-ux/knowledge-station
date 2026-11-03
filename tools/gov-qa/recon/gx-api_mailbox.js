/**
 * getMailboxList: 领导信箱List
 * @APPID: 站点id
 * @SITEID: 信箱ID列表
 * @pageIndex: 当前页数
 * @pageSize: 分页大小
 * @ifPage : 是否显示分页
 * */
function getMailboxList(siteId, appId, pageIndex, pageSize, timetype, ifPage) {
  var url =
    "http://www.gxzf.gov.cn/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs&order=1&siteId=" +
    siteId +
    "&&appId=" +
    appId +
    "&pageSize=" +
    pageSize +
    "&pageIndex=" +
    pageIndex;
  $.get(url, function (data) {
    if (data.statusCode == "200" && data.message == "获取成功") {
      //console.log(data);
      var msglist = data.datas.data;
      $("#lsxd_tb").empty();
      var dataDomain = $("#lsxd_tb").attr("data-domain") || $("#lsxd_tb_list").attr("data-domain");
      dataDomain = dataDomain ? dataDomain.replace(".", "") : "";

      var locationUrl = 'http://gxzf--gov--cn-ce9fe4c69f.zipv6.gxzf.gov.cn';
      // locationUrl = locationUrl.split("list.shtml")[0];
      // locationUrl = locationUrl.split("index.shtml")[0];
      url_sub = locationUrl + dataDomain + "detail.shtml" + "?metadataId=";
      //console.log(url_sub);
      if (msglist.length) {
        //console.log(msglist);
        for (var i = 0; i < msglist.length; i++) {
          if (ifPage) {
            var tempstr = "";
            tempstr =
              '<li class="fn-clear"><div class="mailbox-li-left"><span><strong>留言人：</strong>' +
              msglist[i].USERNAME +
              "</span><span><strong>留言时间：</strong>" +
              timestampToTime(msglist[i].REPLYTIME, timetype) +
              '</span></div><div class="mailbox-li-right">';
            url = url_sub + msglist[i].METADATAID;
            tempstr +=
              "<a href='" +
              url +
              "' target='_blank'><p class='mail-title fs24 bold'>" +
              msglist[i].TITLE +
              '</p><div class="mail-desc">' +
             ( msglist[i].CONTENT.length > 125 ? (msglist[i].CONTENT.substr(0,125) + '...') : msglist[i].CONTENT) +
              "<span>【查看更多】</span></div></a></div></li>";
              $("#lsxd_tb_list").append(tempstr);
          } else {
            var tempstr = "";
            tempstr =
              "<li><span>" +
              timestampToTime(msglist[i].REPLYTIME, timetype) +
              "</span>";
            url = url_sub + msglist[i].METADATAID;
            tempstr +=
              "<a href='" +
              url +
              "' target='_blank'>" +
              msglist[i].TITLE +
              "</a></li>";
              $(".lsxd_tb").append(tempstr);
          }
        }
      }
      if (ifPage) {
        var pageInfo = data.datas.pageInfo;
        createPageHTML(pageInfo.totalResults, 5, pageIndex == 0 ? 0 :Number(pageIndex) - 1, location.pathname.split('.')[0], location.pathname.split('.')[1], 1);
      }
    }
  });
}

/*
 * getMailboxCount：办理情况
 *
 * */
function getMailboxCount(SITEID, APPID) {
  url =
    "/IGI/nbhd/openGovmsgbox.do?method=countGovmsgboxs&appId=" +
    APPID +
    "&siteId=" +
    SITEID;
  $.getJSON(url, function (data) {
    //console.log(data);
    $("#mailboxCount").html(
      "累计收到" +
        data.datas.totalCount +
        "件，已办结" +
        data.datas.finishCount +
        "件"
    );
  });
}
/**
 * getMailboxDetail：查询信件办理情况
 * */

function getMailboxDetail(SITEID) {
  METADATA_ID = parseInt(getUrlParam("metadataId"));
  url =
    "/IGI/nbhd/openGovmsgbox.do?method=viewGovmsgbox&metadataId=" +
    METADATA_ID +
    "&siteId=" +
    SITEID;
  $.getJSON(url, function (data) {
    if (data.statusCode == "200" && data.message == "操作成功") {
      var msginfo = data.datas;
      //      console.log(msginfo);
      $("#message_DEALDEPTID").html(msginfo.DEALDEPTID);
      $("#message_username").html(msginfo.USERNAME);
      $("#message_title").html(msginfo.TITLE);
      $("#message_govmsgboxType").html(govmsgboxType(msginfo.govmsgboxType));
      $("#message_SUBMITTIME").html(timestampToTime(msginfo.SUBMITTIME, 1));
      $("#message_CONTENT").html(msginfo.HTMLCONTENT);

      $("#message_DEALDEPTNAME").html(msginfo.DEALDEPTNAME);
      //console.log(msginfo.REPLYS.length);
      var replyLength = msginfo.REPLYS.length;
      $("#message_REPLYCONTENT").html(
        msginfo.REPLYS[replyLength - 1].REPLYHTMLCONTENT
      );

      //    $('#message_PUBLICTIME').html(timestampToTime(msginfo.FINISHTIME,1));
      $("#message_PUBLICTIME").html(
        timestampToTime(msginfo.REPLYS[replyLength - 1].REPLYTIME, 1)
      );
      $("#message_REPLYDEPT").html(msginfo.REPLYS[replyLength - 1].REPLYDEPT);
      $("#message_REPLYDEPT_gxzf").html(
        msginfo.REPLYS[replyLength - 1].REPLYDEPTEXTNAME
      );
      $("#message_status").html(int2status(msginfo.STATUS));
      var ATTACHLISTArr = msginfo.REPLYS[replyLength - 1].ATTACHLIST;
      //console.log(ATTACHLISTArr.length);
      if (ATTACHLISTArr.length) {
        var addContentHtml = "<p>附件下载：</p>";
        ATTACHLISTArr.forEach(function (item, index) {
          addContentHtml +=
            '<p><a href="' +
            item.FILEPATH +
            '" target="_blank">' +
            item.FILENAME +
            "</a></p>";
          //       console.log(item);
        });
        $("#message_REPLYCONTENT").append(addContentHtml);
      }
    } else {
      alert(data.message + "点击【确定】，返回网站首页");
      window.location.href = "http://" + document.domain;
    }

    $("#message_REPLYCONTENT")
      .add("#message_REPLYCONTENT p")
      .add("#message_REPLYCONTENT font")
      .add("#message_REPLYCONTENT span")
      .add("#message_REPLYCONTENT p *")
      .add("#message_REPLYCONTENT font *")
      .add("#message_REPLYCONTENT span *")
      .each(function () {
        textindent = $(this).css("text-indent");
        textalign = $(this).css("text-align");
        fontweight = $(this).css("font-weight");
        $(this).removeAttr("style");
        if (textindent.indexOf("0") >= 0 || textindent.indexOf("-") >= 0) {
          $(this).css({ "text-indent": "0em" });
        } else {
          $(this).css({ "text-indent": "2em" });
        }
        $(this).css({
          "font-size": "20px",
          "line-height": "36px",
          "font-family": "Microsoft YaHei,SimSun,Arial Narrow",
          "text-align": textalign,
          "font-weight": 400,
        });
      });
  });
}

function govmsgboxType(govmsgboxType) {
  switch (govmsgboxType) {
    case 1:
      return "建议";
      break;
    case 2:
      return "表扬";
      break;
    case 3:
      return "咨询";
      break;
    case 4:
      return "投诉";
      break;
    default:
      return "投诉";
  }
}

/**
 * changeimg：验证码
 * */
function changeimg() {
  url = "/IGI/appadmin/image?randName=loginCaptcha&" + Math.random();
  $("#captchaimg").attr("src", url);
}

/**
 * saveData：提交信件
 * @SITEID: 站点id
 * @APPID: 信箱ID列表
 * @province:省行政区域代码
 * @city: 城市行政区域代码
 * @area: 区域行政区域代码
 * */
function saveData(SITEID, APPID, province, city, area) {
  if ($("#userName").val() == "") {
    alert("申请人姓名不能为空！");
    $("#userName").focus();
    return false;
  }
  var Regex = /^-?\d+$/; //数字
  if (!$("#phone").val().match(Regex)) {
    alert("电话号码格式错误！");
    return false;
  }
  if ($("#location").val() == "") {
    alert("联系地址不能为空！");
    $("#location").focus();
    return false;
  } //邮箱
  /*if($("#email").val() == '') {
      alert("信箱不能为空！");
      $("#email").focus();
      return false;
  }
  var Regex = /\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*/
  /*if(!$("#email").val().match(Regex)) {
      alert("信箱格式错误！");
      $("#email").focus();
      return false;
  }*/
  if ($("#title").val() == "") {
    alert("信件标题不能为空！");
    $("#title").focus();
    return false;
  }
  if ($("#fromContent").val() == "") {
    alert("信件内容不能为空！");
    $("#fromContent").focus();
    return false;
  }
  if ($("#captcha").val() == "") {
    alert("验证码不能为空！");
    $("#captcha").focus();
    return false;
  }

  var title = $("#title").val();
  var content = $("#fromContent").val();
  var govmsgboxType = "2"; //1 建议 2 表扬 3 咨询 4投诉
  var userName = $("#userName").val();
  var sex = $("input[name='sex']:checked").val();
  var phone = $("#phone").val();
  var arePublic = $("input[name='arePublic']:checked").val();
  var location = $("#location").val();
  var email = $("#email").val();
  var htmlContent = $("#content").val();
  var captcha = $("#captcha").val();

  $.ajax({
    url: "/IGI/nbhd/openGovmsgbox.do",
    type: "POST",
    data: {
      method: "openSaveGovmsgbox",
      title: title,
      content: content,
      govmsgboxType: govmsgboxType,
      userName: userName,
      sex: sex,
      phone: phone,
      location: location,
      email: email,
      cardType: "",
      cardId: "",
      arePublic: arePublic, // 0 不公开   1 公开
      isAnonymous: "0", //0 不匿名  1 匿名
      htmlContent: content,
      siteId: SITEID,
      appId: APPID,
      province: province,
      city: city,
      area: area,
      captcha: captcha,
    },
    dataType: "json",
    error: function () {},
    success: function (data) {
      alert(data.message);
      //window.location.reload();
    },
  });
}

/**
 *
 * queryMailboxResult：查询信件
 * @SITEID: 站点id
 * @APPID: 信箱ID列表
 * @userName:姓名
 * @queryPwd: 查询密码
 *
 * */
function queryMailboxResult(SITEID, APPID) {
  var userName = $("#userNameSearch").val();
  var queryPwd = $("#queryPwd").val();

  var url =
    "/IGI/nbhd/openGovmsgbox.do?method=queryResult&siteId=" +
    SITEID +
    "&appId=" +
    APPID +
    "&userName=" +
    userName +
    "&queryPwd=" +
    queryPwd;

  $.getJSON(url, function (data) {
    if (data.statusCode == "200") {
      var msgDatas = data.datas;
      $("#message_title").html(msgDatas.TITLE);
      $("#message_SUBMITTIME").html(timestampToTime(msgDatas.CRTIME, 1));
      $("#message_username").html(msgDatas.USERNAME);
      $("#message_CONTENT").html(msgDatas.HTMLCONTENT);
      var replyLength = msginfo.REPLYS.length;
      $("#message_PUBLICTIME").html(
        timestampToTime(msgDatas.REPLYS[replyLength - 1].REPLYTIME, 1)
      );
      $("#message_REPLYDEPT").html(msgDatas.REPLYS[replyLength - 1].REPLYDEPT);
      $("#message_REPLYCONTENT").html(
        msgDatas.REPLYS[replyLength - 1].REPLYHTMLCONTENT
      );
      $("#replys").show();
    } else {
      alert(data.message);
    }
  });
}

function int2status(parm) {
  var statu;
  parm = parseInt(parm);
  switch (parm) {
    case -1:
      statu = "全部";
      break;
    case 0:
      statu = "草稿";
      break;
    case 1:
      statu = "提交（待整理）";
      break;
    case 3:
      statu = "待分配";
      break;
    case 4:
      statu = "待回复";
      break;
    case 5:
      statu = "待审核";
      break;
    case 7:
      statu = "已办结";
      break;
    case 9:
      statu = "废件";
      break;
    case 10:
      statu = "申办状态";
      break;
    case 11:
      statu = "申请联办中";
      break;
    case 12:
      statu = "联办处理中";
      break;
  }
  return statu;
}