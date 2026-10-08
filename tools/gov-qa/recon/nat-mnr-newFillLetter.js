//JavaScript Doccument
if (top != self) {
    top.location = "error.html";
}
let userId = null;
let xm = null;
let sfzh = null;
let yhsj = null;

function is_mobile() {
    var regex_match = /(nokia|iphone|android|motorola|^mot-|softbank|foma|docomo|kddi|up.browser|up.link|htc|dopod|blazer|netfront|helio|hosin|huawei|novarra|CoolPad|webos|techfaith|palmsource|blackberry|alcatel|amoi|ktouch|nexian|samsung|^sam-|s[cg]h|^lge|ericsson|philips|sagem|wellcom|bunjalloo|maui|symbian|smartphone|midp|wap|phone|windows ce|iemobile|^spice|^bird|^zte-|longcos|pantech|gionee|^sie-|portalmmm|jigs browser|hiptop|^benq|haier|^lct|operas*mobi|opera*mini|320x320|240x320|176x220)/i;
    var u = navigator.userAgent;
    if (null == u) {
        return true;
    }
    var result = regex_match.exec(u);
    if (null == result) {
        return false
    } else {
        return true
    }
}

function QueryString(item) {
    var sValue = location.search.match(new RegExp("[\?\&]" + item + "=([^\&]*)(\&?)", "i"))
    return sValue ? sValue[1] : sValue
}

$(document).ready(function () {
    $.ajax({
        type: "post",
        contentType: "application/json",
        //url: "http://localhost:8091/BaseSystem-1.0.0-SNAPSHOT/mailinfo/mailinfocontroller/savemailinfo",
        // url: "/bzxxww/fillLetter/mailinfocontroller/savemailinfo",
        //url: "http://bjboanda.eicp.net:2000/gtbzxx/mailinfo/mailinfocontroller/savemailinfo",
        url: "/bzxxww/fillLetter/mailinfocontroller/getSessionUser",
        cache: false,
        async: false,
        dataType: "json",
        success: function (result) {
            console.log("result"+result)
            if (is_mobile()) {
                console.log("is_mobile")
                document.location.href = '/bzxxww/pages/wap/wap_new.html';
            }
            if (result.userId != null && result.userId != undefined && result.userId != '') {
                userId = result.userId;
                $("#userId").text(result.userId);
                $("#userName").text(result.userName);
                // xm=result.xm;
                // sfzh=result.sfzh;
                // yhsj=result.yhsj;

                // 填充用户信息到表单
                fillUserInfoToForm(result);

            }
        },
        error: function () {
            layer.close(index);
        }
    });

    let YHID = $("#userId").text();
    let YHM = $("#userName").text();
    if (YHID != null && YHID != undefined && YHID != '') {
        $("#hello").html("欢迎," + YHM+" <a href=\"javascript:;\" onclick=\"openQuitConfirm()\">退出</a>");
        $("#buttonList").after("<a href='/bzxxww/pages/my_list.html' target=\"_blank\" style=\"text-decoration: none;margin-left:10px;border: 1px solid #0953c2;width: 100px;padding:4px 6px;height: 29px;font-weight: 500;font-size: 16px;background-color: white;\">我的建议留言</a>");
    }
    var toJylytime = 10;
    $("#toJyly").attr("disabled", "true");
    $("#toJyly").val('进入建议留言（' + toJylytime-- + '秒）');
    $("#toJyly").css("color", "#333");
    $("#Jylyfrom").hide();
    var interval = setInterval(function () {
        $("#toJyly").val('进入建议留言（' + toJylytime-- + '秒）');
        if (toJylytime < 0) {
            clearInterval(interval);
            $("#toJyly").removeAttr("disabled");
            $("#toJyly").val("进入建议留言");
            $("#toJyly").css("background-color", "#10568a");
            $("#toJyly").css("color", "#fff");
        }
    }, 1000);
});

function openQuitConfirm() {
    layer.confirm("您确定要退出当前登录？", function () {
        $.ajax({
            type: "get",
            url: '/bzxxww/loginout?token=' + localStorage.getItem("token"),
            success: function (result) {
                document.location.reload();
            }
        });
    });
};

function ShowJyly() {
    $.ajax({
        type: "post",
        contentType: "application/json",
        //url: "http://localhost:8091/BaseSystem-1.0.0-SNAPSHOT/mailinfo/mailinfocontroller/savemailinfo",
        // url: "/bzxxww/fillLetter/mailinfocontroller/savemailinfo",
        //url: "http://bjboanda.eicp.net:2000/gtbzxx/mailinfo/mailinfocontroller/savemailinfo",
        url: "/bzxxww/fillLetter/mailinfocontroller/getSessionUser",
        cache: false,
        async: false,
        dataType: "json",
        success: function (result) {
            if (result.userId != null && result.userId != undefined && result.userId != '') {



                $("#toJyly").hide();
                $("#Jylyfrom").show();
            }else{

                document.location.href = "https://dlyz.mnr.gov.cn:8050/tacs-uc/login/index?backUrl=https://box.mnr.gov.cn/bzxxww/fillLetter/mailinfocontroller/zrr/dologin"

                // document.location.href = "https://dlyz.mnr.gov.cn:8050/tacs-uc/login/index?backUrl=http://192.168.155.43:8080/bzxxww/fillLetter/mailinfocontroller/zrr/dologin"

            }
        },
        error: function () {
            layer.close(index);
        }
    });
}

// 填充用户信息到表单的函数
function fillUserInfoToForm(userInfo) {
    console.log("开始填充用户信息到表单:", userInfo);

    // 填充姓名
    if (userInfo.xm) {
        $("#xm").val(userInfo.xm);
        console.log("填充姓名:", userInfo.xm);
    }

    // 填充身份证号
    if (userInfo.sfzh) {
        $("#sfzh").val(userInfo.sfzh);
        console.log("填充身份证号:", userInfo.sfzh);
    }

    // 填充手机号码
    if (userInfo.yhsj) {
        $("#phone").val(userInfo.yhsj);
        console.log("填充手机号码:", userInfo.yhsj);
    }

    // 填充电子邮箱
    if (userInfo.yhemail) {
        $("input[name='email']").val(userInfo.yhemail);
        console.log("填充邮箱:", userInfo.yhemail);
    }





    console.log("用户信息填充完成");
}

function isvali() {
    var LXR = document.send.name.value;
    var LXRSFZ = document.send.IDCard.value;
    var LXRDH = document.send.phone.value;
    var LXRYX = document.send.email.value;
    var XJBT = document.send.title.value;
    var XJNR = document.send.content.value;
    var XJLX = document.send.mailType.value;
    XJLX = $("input[name='mailType']:checked").val();
    var LXRDZ = document.send.address.value;
    var PROVINCE = $("#province option:selected").text();
    ;
    var CITY = $("#city option:selected").text();
    var DISTRICT = $("#district option:selected").text();
    var SSX = PROVINCE + "-" + CITY + "-" + DISTRICT;
    // var YZM = document.send.validCode.value;
    var SFTSJB = "";
    var obj = document.getElementsByName("SFTSJB");
    for (var i = 0; i < obj.length; i++) {
        if (obj[i].checked) {
            SFTSJB = obj[i].value;
        }
    }
    var ts = new Array();
    ;
    if (LXR == "") {
        ts.push("姓名");
    }
    if (LXRSFZ == "") {
        ts.push("身份证号");
    }
    if (LXRDH == "") {
        ts.push("手机号码");
    }
    if (LXRYX == "") {
        ts.push("电子邮箱");
    }
    if (LXRDZ == "") {
        ts.push("地址");
    }
    if (XJBT == "") {
        ts.push("信件标题");
    }
    if (XJNR == "") {
        ts.push("信件内容");
    }
    // if (YZM == "") {
    //     ts.push("验证码");
    // }
    if (ts.length != 0) {
        var nullts = ts.join("、")
        layer.alert(nullts + "不能为空！", {offset: "200px", title: '提示'});
        return;
    }
    if (SFTSJB == "") {
        layer.alert("请选择是否含有投诉举报内容！", {offset: "200px", title: '提示'});
        return;
    }

    if (LXR == "") {
        layer.alert("姓名不能为空！", {offset: "200px", title: '提示'});
        return;
    } else {
        var pattern = /^[\u4E00-\u9FA5]{1,6}$/;
        if (pattern.test(LXR) == false) {
            layer.alert("请输入正确的姓名！", {offset: "200px", title: '提示'});
            return;
        }
    }
    if (LXRSFZ == "") {
        layer.alert("身份证号不能为空！", {offset: "200px", title: '提示'});
        return;
    } else {
        if (cidInfo(LXRSFZ) == false) {
            layer.alert("输入正确的身份证号码！", {offset: "200px", title: '提示'});
            return;
        }
    }

    if (LXRDH == "") {
        layer.alert("手机号码不能为空！", {offset: "200px", title: '提示'});
        return;
    } else {
        var pattern = /^1[3456789]\d{9}$/;
        if (pattern.test(LXRDH) == false) {
            layer.alert("输入正确的手机号码！", {offset: "200px", title: '提示'});
            return;
        }
    }

    if (LXRYX == "") {
        layer.alert("电子邮箱不能为空！", {offset: "200px", title: '提示'});
        return;
    } else {
        if (!isEmail(LXRYX)) {
            layer.alert("输入正确的电子邮箱！", {offset: "200px", title: '提示'});
            return;
        }
    }

    if (LXRDZ == "") {
        layer.alert("地址不能为空！", {offset: "200px", title: '提示'});
        return;
    } else {
        if (LXRDZ.length > 25) {
            layer.alert("地址不能超过25个字！", {offset: "200px", title: '提示'});
            return;
        }
        if (LXRDZ.length <= 3) {
            layer.alert("地址不能少于3个字！", {offset: "200px", title: '提示'});
            return;
        }
    }

    if (XJBT == "") {
        layer.alert("信件主题不能为空！", {offset: "200px", title: '提示'});
        return;
    } else {
        if (XJBT.length > 50) {
            layer.alert("信件主题不能超过50个字！", {offset: "200px", title: '提示'});
            return;
        }
    }
    if (XJNR == "") {
        layer.alert("信件内容不能为空！", {offset: "200px", title: '提示'});
        return;
    } else {
        if(XJLX=="ZX"){
            if (XJNR.length > 200) {
                layer.alert("信件内容不能超过200个字！", {offset: "200px", title: '提示'});
                return;
            }
        }else{
            if (XJNR.length > 300) {
                layer.alert("信件内容不能超过300个字！", {offset: "200px", title: '提示'});
                return;
            }
        }
    }
    // if (YZM == '') {
    //     layer.alert("验证码不能为空！", {offset: "200px", title: '提示'});
    //     return;
    // }
    $.ajax({
        type: "post",
        contentType: "application/json",
        //url: "http://localhost:8091/BaseSystem-1.0.0-SNAPSHOT/mailinfo/mailinfocontroller/savemailinfo",
        // url: "/bzxxww/fillLetter/mailinfocontroller/savemailinfo",
        //url: "http://bjboanda.eicp.net:2000/gtbzxx/mailinfo/mailinfocontroller/savemailinfo",
        url: "/bzxxww/fillLetter/mailinfocontroller/getSessionUser",
        cache: false,
        async: true,
        dataType: "json",
        success: function (result) {
            if (result.userId != null && result.userId != undefined && result.userId != '') {
            }else{
                document.location.href = "https://dlyz.mnr.gov.cn:8050/tacs-uc/login/index?backUrl=https://box.mnr.gov.cn/bzxxww/fillLetter/mailinfocontroller/zrr/dologin"
                // document.location.href = "https://dlyz.mnr.gov.cn:8050/tacs-uc/login/index?backUrl=http://192.168.155.43:8080/bzxxww/fillLetter/mailinfocontroller/zrr/dologin"
            }
        },
        error: function () {
            layer.close(index);
        }
    });
    //loading层
    var index = 0; //0代表加载的风格，支持0-2
    $.ajax({
        type: "post",
        contentType: "application/json",
        beforeSend: function () {
            index = layer.load(0, {shade: [0.1, '#fff'], offset: "200px", title: '提示'});
        },
        //url: "http://localhost:8091/BaseSystem-1.0.0-SNAPSHOT/mailinfo/mailinfocontroller/savemailinfo",
        url: "/bzxxww/fillLetter/mailinfocontroller/savemailinfo",
        //url: "http://bjboanda.eicp.net:2000/gtbzxx/mailinfo/mailinfocontroller/savemailinfo",
        // url: "http://localhost:8080/bzxxww/mailinfo/mailinfocontroller/savemailinfo",
        data: JSON.stringify({
            LXR: LXR,
            LXRSFZ: LXRSFZ,
            LXRDH: LXRDH,
            LXRYX: LXRYX,
            XJBT: XJBT,
            XJNR: XJNR,
            XJLX: XJLX.toUpperCase(),
            LXRDZ: LXRDZ,
            SSX: SSX,
            // YZM: YZM,
            LY: "部网站"
        }),
        cache: false,
        //async : false,
        dataType: "json",
        success: function (result) {
            layer.close(index);
            layer.alert(result.resp_msg, {offset: "200px", title: '提示'});
            if (result.resp_msg.indexOf("信件投递成功!")) {
                document.send.reset();
            }
        },
        error: function () {
            layer.close(index);
            layer.alert("信件投递失败!", {offset: "200px", title: '提示'});
        }
    });
}

function isEmail(s) {
    //var patrn = /^\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$/;
    var patrn = /^\w+@[a-z0-9]+\.[a-z]{2,4}$/;

    if (!patrn.exec(s)) {
        return false;
    }
    return true;
}

var aCity = {
    11: "北京",
    12: "天津",
    13: "河北",
    14: "山西",
    15: "内蒙古",
    21: "辽宁",
    22: "吉林",
    23: "黑龙江",
    31: "上海",
    32: "江苏",
    33: "浙江",
    34: "安徽",
    35: "福建",
    36: "江西",
    37: "山东",
    41: "河南",
    42: "湖北",
    43: "湖南",
    44: "广东",
    45: "广西",
    46: "海南",
    50: "重庆",
    51: "四川",
    52: "贵州",
    53: "云南",
    54: "西藏",
    61: "陕西",
    62: "甘肃",
    63: "青海",
    64: "宁夏",
    65: "新疆",
    71: "台湾",
    81: "香港",
    82: "澳门",
    91: "国外"
}

function cidInfo(sId) {
    var iSum = 0
    var info = ""
    if (!/^\d{17}(\d|x)$/i.test(sId)) return false;
    sId = sId.replace(/x$/i, "a");
    if (aCity[parseInt(sId.substr(0, 2))] == null) return false;
    sBirthday = sId.substr(6, 4) + "-" + Number(sId.substr(10, 2)) + "-" + Number(sId.substr(12, 2));
    var d = new Date(sBirthday.replace(/-/g, "/"))
    if (sBirthday != (d.getFullYear() + "-" + (d.getMonth() + 1) + "-" + d.getDate())) return false;
    for (var i = 17; i >= 0; i--) iSum += (Math.pow(2, i) % 11) * parseInt(sId.charAt(17 - i), 11)
    if (iSum % 11 != 1) return false;
    return aCity[parseInt(sId.substr(0, 2))] + "," + sBirthday + "," + (sId.substr(16, 1) % 2 ? "男" : "女")
}

function tsjb() {
    //layer.confirm('确定跳转到投诉举报页面吗?',{btn:['是','否']},function(){
    layer.alert("“建议留言”栏目不受理投诉和举报、个案问题（如某一行为是否违法、如何处理、如何执行等）、法律适用解释问题（如新旧土地管理法如何衔接、非法占用耕地林地以外的农用地是否构成犯罪、村民占用耕地建住宅由谁管辖、没收的地上建筑构物如何处置）等事项，如有此类内容，将作为无效建议留言处理，请您认真核对建议留言内容。投诉和举报等事项请通过其他途径办理；个案问题请向行为发生地的县级自然资源主管部门反映，不服自然资源主管部门对案件的处理等，可通过行政复议、行政诉讼等法律途径寻求救济；法律适用解释问题请向当地县级自然资源主管部门反映，当地自然资源主管部门无法解答的，由其逐级向上反映。" +
        "<br>感谢您对我部工作的关注、理解和支持！!", {title: '提示'});
    $("#SFTSJB").removeAttr("checked");
    $("#SFTSJB2").attr("checked", "checked");

    // $.ajax({
    //     type: "post",
    //     contentType: "application/json",
    //     beforeSend:function(){
    //     	index = layer.load(0, {shade: [0.1,'#fff'] });
    //     },
    //    	//url: "http://bjboanda.eicp.net:2000/gtbzxx/mailinfo/mailinfocontroller/savemailinfo",
    //    	//url: "http://localhost/bzxx/mailinfo/mailinfocontroller/saveTsjbjl",
    //    	url: "http://localhost:8080/bzxxww/fillLetter/mailinfocontroller/saveTsjbjl",
    //     cache: false,
    //     //dataType: "json",
    //     success: function (result){
    //     	layer.close(index);
    //     	window.open(tsjburl);//跳转到投诉举报页面
    //     },
    //     error:function () {
    //     	layer.close(index);
    //     }
    //  });
}

//});

//获取验证码
function getValidCode() {
    var phone = $("#phone").val();
debugger
    if (phone == '') {
        layer.alert("请输入手机号码", {offset: "200px", title: '提示'});
        return false;
    } else {
        var pattern = /^1[3456789]\d{9}$/;
        if (pattern.test(phone) == false) {
            layer.alert("请输入正确的手机号码<br>", {offset: "200px", title: '提示'});
            return;
        }
    }

    var time = 60;
    $("#validCodeBtn").attr("disabled", "true");
    $("#validCodeBtn").val('剩余' + time-- + '秒');
    var interval = setInterval(function () {
        $("#validCodeBtn").val('剩余' + time-- + '秒');
        if (time < 1) {
            clearInterval(interval);
            $("#validCodeBtn").removeAttr("disabled");
            $("#validCodeBtn").val("获取验证码");

        }
    }, 1000);
    $.ajax({
        type: "post",
        contentType: "application/json",
        //url: "http://localhost:8091/BaseSystem-1.0.0-SNAPSHOT/mailinfo/mailinfocontroller/getValidCode",
        url: "/bzxxww/fillLetter/mailinfocontroller/getValidCode",
        //url: "http://bjboanda.eicp.net:2000/gtbzxx/mailinfo/mailinfocontroller/getValidCode",
        //url: "http://localhost/bzxx/mailinfo/mailinfocontroller/getValidCode",
        data: phone,
        dataType: "json",
        async: true,
        success: function (result) {
            if (result == "" || result == null) {
                layer.alert("获取验证码过于频繁，请您1分钟后再试!", {offset: "200px", title: '提示'});
            }
        },
        error: function (e) {
            layer.alert("验证码发送失败!", {offset: "200px", title: '提示'});
        }
    });
}
