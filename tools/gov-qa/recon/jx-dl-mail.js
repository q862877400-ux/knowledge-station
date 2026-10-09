// 办件分类
var mailFormData = {};
// var _bjType = commonApi.getParams('bjtype') || ''
var docType = [{
    name: "身份证",
    id: "1",
    // id: "1645602112146427904"
  }, {
    name: "军官证",
    id: "2",
    // id: "1645602310943854592"
  },
  {
    name: "其他",
    id: "3",
    // id: "1645602310943854593"
  }
];
// 来信目的
var aimIdArr = [
  
  { name: "我向省长建言", id: "1751837275901734912"},
 
]// 来信目的
var _contentType = [
  { name: "办事服务", id: "1751836962868244480"},
  { name: "一号发展工程", id: "1773536766395990016"},
  { name: "营商环境", id: "1751837023186530304"},
  { name: "教育", id: "1751837071559438336"},
  { name: "医疗", id: "1773536109991608320"},
  { name: "养老", id: "1773536155994734592"},
  { name: "住房", id: "1773536194318090240"},
  { name: "就业创业", id: "1773536229025955840"},
  { name: "社会保障", id: "1773536269937197056"},
  { name: "居民收入", id: "1773536304536010752"},
  { name: "经济政策", id: "1773536340481196032"},
  { name: "生态环保", id: "1773536373465202688"},
  { name: "精准脱贫", id: "1773536435704479744"},
  { name: "科研创新", id: "1773536465148493824"},
  { name: "对外开放", id: "1773536495741747200"},
  { name: "新型城镇化", id: "1773536537944834048"},
  { name: "物流交通", id: "1773536577228685312"},
  { name: "农业农村", id: "1773536618420944896"},
  { name: "生活消费", id: "1773536652373835776"},
  { name: "文化体育", id: "1773536683516542976"},
  { name: "退役军人", id: "1773536724897546240"},
  { name: "其它", id: "1773536801808498688"},
];

layui.use(['form', 'layer'], function () {
  var form = layui.form;
  //渲染留言分类
  // getRelateinfo();
  //证件类型
  renderSelect('#contentTypeId',_contentType);
  renderSelect('#docType', docType);
  renderSelect('#aimId', aimIdArr);
  form.render('select');
  
  setTimeout(function () {
    form.render('select');
  }, 100);
  // 获取用户信息
  getUserInfo(function (res) {
    mailFormData = {
      name: res.name,
      email: res.email,
      phone: res.mobile,
      docIdNum: res.cardid || res.corusercardid,
    };
    var paperstypeName = res.paperstypeName;
    if(paperstypeName == '' || paperstypeName == null || paperstypeName == undefined){ 
      paperstypeName = '身份证'
    }
    docType.forEach(function (elem) {
      if (elem.name == paperstypeName) {
          mailFormData.docType = elem.id
      }
    })
    $("#name").val(mailFormData.name).attr('disabled', 'disabled');
    $("#phone").val(mailFormData.phone);
    if (mailFormData.email) {
      $("#email").val(mailFormData.email).attr('disabled', 'disabled');
    }
    $("#docType").val(mailFormData.docType).attr('disabled', 'disabled');
    $("#docIdNum").val(mailFormData.docIdNum).attr('disabled', 'disabled');
    // form.render('select');

  }, function (res) {});


  //自定义验证
  form.verify({
    /*identity: function(val){
        var regIdNo = /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/;
        if(!regIdNo.test(val)){
            layer.msg('身份证号填写有误');
            return false;
        }
    },*/
    name: function (val) {
      if (val.length > 50) {
        return '姓名最大长度50'
      }
      var arrowReg = /<|>/
      if (arrowReg.test(val)) return '不能含有尖括号'
    },
    phone: function (val) {
      if (mailFormData.phone) {
        val = mailFormData.phone;
      }
      var reg =
        /^(?:(?:\+|00)86)?1(?:(?:3[\d])|(?:4[5-79])|(?:5[0-35-9])|(?:6[5-7])|(?:7[0-8])|(?:8[\d])|(?:9[1589]))\d{8}$/g
      if (!reg.test(val)) {
        return '手机号格式不正确'
      }
    },
    postCode: function (val) {
      var regCode = /^(0[1-7]|1[012356]|2[0-7]|3[0-6]|4[0-7]|5[1-7]|6[1-7]|7[1-5]|8[1345]|9[09])\d{4}$/
      if (val && !regCode.test(val)) {
        return '邮政编码格式不正确'
      }
    },
    address: function (val) {
      if (val.length > 50) {
        return '联系地址最大长度50'
      }
      var arrowReg = /<|>/
      if (arrowReg.test(val)) return '不能含有尖括号'
    },
    email: function (value) {
      if (value.length > 50) return '电子邮箱最大长度50'
      // 先验证不允许有中文
      var CNchartReg = new RegExp('[\\u4E00-\\u9FFF]+', 'g')
      // 验证必须有@和.
      var reg1 = /^[0-9a-zA-Z]+[@]+[0-9a-zA-Z]+[\.]+/
      // 验证出了@.外不允许有特殊符号
      var reg2 = /[`~!#$%^&*()_\-+=<>?"{}|,;'\\[\]·~！#￥%……&*（）——\-+={}|《》？:\/：“”【】、；‘'，。、]/im

      if (
        value.indexOf('..') > -1 ||
        !reg1.test(value) ||
        reg2.test(value) ||
        value.split('@').length > 2 ||
        CNchartReg.test(value)
      )
        return '不是有效的电子邮件地址'
    },
    title: function (val) {
      if (val.length > 200) {
        return '信件标题最大长度200'
      }
      var arrowReg = /<|>/
      if (arrowReg.test(val)) return '不能含有尖括号'
    },
    content: function (val) {
      if (val.length > 50000) {
        return '信件内容最大长度50000'
      }
      var arrowReg = /<|>/
      if (arrowReg.test(val)) return '不能含有尖括号'
    }
  })

  form.on('submit(add)', function (data) {
    // console.log('field: ', data.field);
    var _data = {
      tenantId: defaultConfig.userIdObj.tenantId,
      deptId: defaultConfig.userIdObj.deptId,
      siteId: defaultConfig.userIdObj.qdId,
      // name: mailFormData.name,
      // phone: mailFormData.phone,
      sourceId: "1", // 信件来源 1-我向省长建言 （字典ics_mail_source）
      problemArea: 'jxsrmzf' // 问题区域 必填 
    }
    // console.log('sub: ', Object.assign(data.field, _data))

    mailSub(Object.assign(data.field, _data))
    return false
  })

  imgCode();
  $('#yzmimg').on('click', function () {
    imgCode();
  })

});


//信件提交
function mailSub(params) {
  $.ajax({
    url: '/api/mail/add',
    type: 'post',
    contentType: 'application/json',
    data: JSON.stringify(params),
    success: function (res) {
      if (res.success == '添加成功') {
        resetParams()
        layui.use('layer', function () {
          imgCode();
          var layer = layui.layer
          layer.alert('信件已提交成功，请到用户中心查询。<br>' + '您的查询码为：' + res.searchCode);
        })
        getMsg({
          phone: params.phone,
          code: res.searchCode
        })
      }
    },
    error: function (err) {
      console.log(err)
      var _errObj = JSON.parse(err.responseText)
      layui.use('layer', function () {
        var layer = layui.layer
        layer.msg($.isArray(_errObj.errors) ? _errObj.errors[0].msg : _errObj.errors)
      })
    }
  })
}


// 下拉框
function renderSelect(dom, data) {
  var _option = '<option value="">请选择</option>';
  $.each(data, function (key, elem) {
    if (elem) {
      var isSelected = '';
      if (dom == '#aimId') {
        isSelected = 'selected';
      }
      if (elem.id) {
        _option += '<option ' + isSelected + ' value="' + elem.id + '">' + elem.name + '</option>';
      } else {
        _option += '<option ' + isSelected + ' value="' + elem.name + '">' + elem.name + '</option>';
      }
    }
  });
  $(dom).html(_option);
}


function imgCode() {
  // $('#yzmimg').attr('src', '/api/captcha/getimg?' + Math.random())
  $.ajax({
    url: "/api/captcha/getimg?" + Math.random(),
    type: "get",
    success: function (res) {
      if (res) {
        $('#yzmimg').attr('src', res.captchaImg);
        $('#captchaKey').val(res.key);
      }
    },
    error: function error(err) {}
  });
}

//重置
function resetParams() {
  layui.use(['form'], function () {
    var form = layui.form;

    $("#name").val(mailFormData.name).attr('disabled', 'disabled');
    $("#phone").val(mailFormData.phone);
    if (mailFormData.email) {
      $("#email").val(mailFormData.email).attr('disabled', 'disabled');
    }
    $("#docType").val(mailFormData.docIdNum).attr('disabled', 'disabled');
    $("#docIdNum").val(mailFormData.docIdNum).attr('disabled', 'disabled');

    $('#postCode').val('');
    $('#address').val('');

    $('#title').val('');
    $('#content').val('');
    $('#captcha').val('');
    $('#phoneCode').val('');

    $('#aimId').find('option').eq(0).prop('selected', true);
    $('#contentTypeId').find('option').eq(0).prop('selected', true);

    form.render('select')
  })
}

//获取信件来信目的、内容分类
function getRelateinfo() {
   layui.use(['form'], function () {
       var form = layui.form;
      $.ajax({
        url: '/api/mail/relateinfo',
        type: 'get',
        data: {
          tenantId: defaultConfig.userIdObj.tenantId,
          // deptId: '',
          deptId: defaultConfig.userIdObj.deptId,
          adminFlag: 1
        },
        success: function (res) {
           
            form.render('select');
        
        },
        error: function (err) {
          console.log(err)
        }
    })
 })
}

// 手机验证码
function getphoneVerify() {
  $.ajax({
    type: "get",
    url: '/api/ysqgk/sendMessage',
    dataType: "json",
    data:{
      phone:$('#phone').val(),
      type: 1, //短信类型 [必填] 值为0或1，0：为依申请，1为信件
    },
    success: function success(res) {
       if(res.code=='200'){ 
            layui.use('layer', function () {
                var layer = layui.layer
                layer.alert(res.data);
            })
            
        $("#phone").attr('disabled','disabled');
      }
    },
    error: function error(error) {
      console.log(error);
    }
  });
}
