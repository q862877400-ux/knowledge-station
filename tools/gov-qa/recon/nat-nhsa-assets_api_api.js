// 源代码可用es6+写
function addScript() {
    document.write("<script language=javascript src=" + "./../../assets/toast.js" + "></script>");
}
addScript();
jQuery.support.cors = true;
var errorCount = 0
jQuery.ajaxSetup({
    xhr: function xhr() {
        if (window.ActiveXObject) {
            return new window.ActiveXObject("Microsoft.XMLHTTP");
        } else {
            return new window.XMLHttpRequest();
        }
    },
    error: function error() { },
    // finally
    complete: function complete(xhr, status) {
        var responseText = JSON.parse(xhr.responseText);

        if (responseText && responseText.code !== 20000) {
            errorCount++;

            if (errorCount < 5) {
                window.renderRecaptcha && renderRecaptcha();
            }
        }
        toastErr(Number(xhr.status), xhr, responseText.message);
    }
});
// 集中处理code
function toastErr(code, xhr, message) {
    var data = JSON.parse(xhr.responseText);
    switch (code) {
        case 429:
            showAlert("您的操作太频繁，请稍后再试。");
            break;
        case 500:
            if (message === "验证码错误") {
                showAlert("验证码输入有误，请重新输入");
                break;
            }
        // showAlert('服务器开小差了,请联系管理员。');break;
        default:
            break;
    }
}
// var production = 'http://172.16.20.43:30013';
// 测试
//  var production = 'http://10.18.104.32:30013';
//线上
// var production = 'http://120.132.73.61:30013';
// 测试
// var production = 'http://42.81.122.151:30013';
// var production = 'http://172.16.120.114:30013';
// var production = 'http://172.16.120.179:30013';
// var production = 'http://172.16.120.22:30013';  // 本地
// var production = 'http://172.16.20.177:30013';  
// var production = 'http://10.18.104.32:30013'; // 开发环境
// var production = 'http://10.200.152.19:30013'; // 开发环境
// var production = 'https://172.17.26.220:30013'; // 开发环境
// var production = 'https://cap-test.nhsa.gov.cn:7913'; // 开发环境
// var production = 'https://cap-test.nhsa.gov.cn:30013'; // 医保局测试服
// var production = 'http://120.132.73.61:30013'; // 线上环境

// var production = 'http://172.18.24.211:30013';  // 2024年5月23日 更新的端口(测试环境)
// var production_c = 'http://172.18.24.211:30015';  // 2024年5月23日 新来信类别使用(测试环境)

// var production = 'http://219.143.42.61:7913';  // 2024年5月27日 更新的端口
// var production_c = 'http://219.143.42.61:7915';  // 2024年5月27日 新来信类别

// var production = 'http://10.18.104.32:30013'; // 开发环境
// var production_c = 'http://10.18.104.32:30015';  // 新来信类别使用(开发环境)

// var production = 'http://10.200.153.16:30013';  // 2022年5月7日更新的端口(测试环境)
// var production_c = 'http://10.200.153.16:30015';  // 2023年10月17日 新来信类别使用(测试环境)

var production = "https://cap.nhsa.gov.cn:7913"; // 正式环境
var production_c = "https://cap.nhsa.gov.cn:7915"; // 新来信类别使用(正式环境)

var api = {
    recaptcha: function recaptcha(config) {
        $.ajax({
            type: "post",
            url: production + "/oauth/captcha",
            headers: {
            },
            contentType: "application/json",
            // url: production + '/oauth/captcha?captchaKey=' + config.code,
            data: JSON.stringify({
                captchaKey: config.code
            }),
            success: config.success,
            error: config.fail
        });
    },
    verifyRecaptcha: function verifyRecaptcha(config) {
        console.log(config);
        $.ajax({
            type: "get",
            url: production + "/oauth/verifyCaptcha?captchaCode=" + config.data.captchaCode + "&captchaKey=" + config.data.captchaKey,
            success: config.success,
            error: config.fail
        });
    },
    login: function login(config) {
        $.ajax({
            type: "post",
            url: production + "/oauth/login",
            data: config.data || {},
            success: config.success,
            error: config.fail
        });
    },
    sendEmail: function sendEmail(config) {
        $.ajax({
            type: "post",
            url: production + "/user/mail",
            contentType: "application/json;charset=UTF-8",
            data: config.data || {},
            success: config.success,
            error: config.fail
        });
    },
    register: function register(config) {
        $.ajax({
            type: "post",
            url: production + "/user/register",
            data: config.data || {},
            contentType: "application/json",
            success: config.success,
            error: config.fail
        });
    },
    // 邮箱验证
    verify: function verify(config) {
        $.ajax({
            type: "get",
            url: production + "/user/register/verify/" + config.code,
            contentType: "application/json",
            success: config.success,
            error: config.fail
        });
    },
    // 忘记密码 - 邮箱验证 : 废弃
    pwdVerifyFq: function pwdVerify(config) {
        console.log(config);
        $.ajax({
            type: "get",
            url: production + "/user/findpsw/exist?captchaCode=" + config.data.captchaCode + "&captchaKey=" + config.data.captchaKey + "&email=" + config.data.email,
            contentType: "application/json",
            success: config.success,
            error: config.fail
        });
    },
    // 忘记密码 - 邮箱验证
    pwdVerify: function pwdVerify(config) {
        console.log(config);
        $.ajax({
            type: "post",
            url: production + "/user/findPsw",
            contentType: "application/json",
            data: JSON.stringify(config.data),
            success: config.success,
            error: config.fail
        });
    },
    // 忘记密码 - 重置密码 : 废弃
    resetPasswordFq: function resetPasswordFq(config) {
        $.ajax({
            type: "post",
            url: production + "/user/updatePsw",
            data: config.data || {},
            contentType: "application/json",
            success: config.success,
            error: config.fail
        });
    },
    resetPassword: function resetPassword(config) {
        $.ajax({
            type: "post",
            url: production + "/user/updatePsw",
            data: config.data || {},
            contentType: "application/json",
            success: config.success,
            error: config.fail
        });
    },
    // 获取级联选择
    addressAll: function addressAll(config) {
        $.ajax({
            type: "get",
            url: production + "/address/all",
            contentType: "application/json",
            success: config.success,
            error: config.fail
        });
    },
    // 办理统计列表接口
    hanleStatistics: function hanleStatistics(data, success, fail) {
        $.ajax({
            type: "post",
            url: production + "/open/netizen/handleStatisticsList",
            contentType: "application/json",
            data: JSON.stringify(data),
            success: success,
            error: fail
        });
    },
    // 办理统计详情接口
    hanleDetail: function hanleDetail(data, success, fail) {
        $.ajax({
            type: "get",
            url: production + "/open/netizen/handleStatisticsDetail?id=" + data,
            contentType: "application/json",
            success: success,
            error: fail
        });
    },
    // 交流公开列表接口
    exchangeOpen: function exchangeOpen(data, success, fail) {
        $.ajax({
            type: "post",
            url: production + "/open/netizen/openInfoList",
            contentType: "application/json",
            data: JSON.stringify(data),
            success: success,
            error: fail
        });
    },
    // 交流公开详情接口
    openDetail: function openDetail(data, success, fail) {
        $.ajax({
            type: "get",
            url: production + "/open/netizen/openInfoDetail?id=" + data,
            contentType: "application/json",
            success: success,
            error: fail
        });
    },
    // 交流公开详情接口
    letterType: function letterType(config) {
        var token = JSON.parse(sessionStorage.getItem("user"));
        $.ajax({
            type: "post",
            headers: {
                "Authorization": "bearer " + token.authToken.accessToken
            },
            url: production + "/capLetter/dictionary/queryByCode",
            data: {
                "code": "letter_online"
            },
            success: config.success,
            error: config.fail
        });
    },
    letterBox: function letterBox(config) {
        var token = JSON.parse(sessionStorage.getItem("user"));
        $.ajax({
            headers: {
                "Authorization": "bearer " + token.authToken.accessToken
            },
            type: "post",
            url: production + "/capLetter/dictionary/queryByCode",
            data: {
                "code": "letter_box"
            },
            success: config.success,
            error: config.fail
        });
    },
    problemSolving: function problemSolving(config) {
        var token = JSON.parse(sessionStorage.getItem("user"));
        $.ajax({
            type: "post",
            headers: {
                "Authorization": "bearer " + token.authToken.accessToken
            },
            url: production + "/capLetter/dictionary/queryByCode",
            data: {
                "code": "problem_solving"
            },
            success: config.success,
            error: config.fail
        });
    },
    // 新的来信类别
    newClasify: function newClasify(config) {
        $.ajax({
            type: "get",
            url: production_c + "/biz-api/cap/v1/register/dictionary/classify?classify=".concat(config.query),
            contentType: "application/json",
            success: config.success,
            error: config.fail
        });
    },
    // 信访form提交
    capLetterInsert: function capLetterInsert(data, success, fail) {
        var token = JSON.parse(sessionStorage.getItem("user"));
        $.ajax({
            type: "post",
            headers: {
                "Authorization": "bearer " + token.authToken.accessToken
            },
            url: production + "/capLetter/insert",
            contentType: "application/json",
            data: JSON.stringify(data),
            success: success,
            error: fail
        });
    },
    // 留言查询
    messageQuery: function messageQuery(data, success, fail) {
        console.log(data, "queryquery");
        var token = JSON.parse(sessionStorage.getItem("user"));
        $.ajax({
            type: "get",
            headers: {
                "Authorization": "bearer " + token.authToken.accessToken
            },
            url: production + "/oauth/message/query?email=".concat(data.email, "&channel=").concat(data.channel, "&pageNum=").concat(data.page, "&pageSize=").concat(data.size),
            contentType: "application/json",
            // data: JSON.stringify(data),
            success: success,
            error: fail
        });
    },
    messageDetail: function messageQuery(data, success, fail) {
        console.log(data, "queryquery");
        var token = JSON.parse(sessionStorage.getItem("user"));
        $.ajax({
            type: "get",
            headers: {
                "Authorization": "bearer " + token.authToken.accessToken
            },
            url: production + "/oauth/message/detail?id=".concat(data),
            contentType: "application/json",
            // data: JSON.stringify(data),
            success: success,
            error: fail
        });
    },
    // 下载附件
    downLoadFileById: function downLoadFileById(data, success, fail) {
        var token = JSON.parse(sessionStorage.getItem("user"));
        $.ajax({
            type: 'get',
            headers: {
                "Authorization": "bearer " + token.authToken.accessToken
            },
            responseType: 'arraybuffer',
            url: production_c + '/biz-api/cap/v1/attachment/download?id='.concat(data),
            success: success,
            fail: fail
        })

    }
};

