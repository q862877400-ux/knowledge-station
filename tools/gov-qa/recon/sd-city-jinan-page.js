layui.use(['table', 'laydate'], function () {
  var table = layui.table;
  var laydate = layui.laydate;
  var href = window.location.href;
  var _url = '/jpaas-jact-web-server/front/';
  if (href.indexOf('api-gateway') != -1) {
    _url = '/api-gateway' + _url;
  }
  if (href === 'about:srcdoc' && _url.indexOf('api-gateway') === -1) {
    _url = '/api-gateway' + _url;
  }
  //第一个实例
  var tableIns = table.render({
    elem: 'table',
    url: _url + 'find-mail-pub-list', //数据接口
    page: {
      theme: '#3366cc'
    }, //开启分页
    cols: [
      [ //表头
        {
          field: 'transactNo',
          title: '信件编号',
          width: 200,
        },
        {
          field: 'title',
          title: '标题',
          width: 360,
          templet: "<div class='df_tit'><a href='" + _url + "mail-pub-detail?iid={{d.iid}}' style='color: black;' class='layui-table-link' >{{d.title}}</a></div>"
        },
        {
          title: '处理情况',
          width: 125,
          templet: function () {
            var clqk = '处理完毕'
            return clqk;
          }
        },
        {
          field: 'submitDate',
          title: '提交时间',
          width: 136,
          templet: function (d) {
            return timestampToDate(d.submitDate);
          }
        },
        {
          field: 'submitTargetName',
          title: '提交部门',
          width: 234,
        }
      ]
    ],
    request: {
      pageName: 'pageNum' //页码的参数名称，默认：page
      ,
      limitName: 'pageSize' //每页数据量的参数名，默认：limit
    },
    where: {
      platformUid: $("#platformUid").val(),
      submitTargetIds:$("#submitTargetIds").val(),
	  govOpen:$("#govOpen").val(),
	  _t: new Date().getTime() // 防缓存
    }
  });

  var rangeTime;
  // var platformUid = $(".center_1 #platformUid").val();
  // var titleOrContent = $(".center_1 .searchone").val();
  //日期范围
  laydate.render({
    elem: '#time',
    range: '~',
    theme: '#3366cc',
    done: function (value, date, endDate) {
      rangeTime = value;
      // console.log(date); //得到日期时间对象：{year: 2017, month: 8, date: 18, hours: 0, minutes: 0, seconds: 0}
      // console.log(endDate); //得结束的日期时间对象，开启范围选择（range: true）才会返回。对象成员同上。
    }
  });


  $('.searchtwo').click(function () {
    // var str = document.all.area;
    // var area = '';
    // for (var i = 0; i < str.length; i++) {
    //   console.log(str[i].value);
    //   if(str[i].value != '') {
    //     area = area + str[i].value + ',';
    //   }
    // };
    // if(area.length > 0) {
    //   area = area.substring(0,area.length-1);
    // }
    tableIns.reload({
      request: {
        pageName: 'pageNum', //页码的参数名称，默认：page
        limitName: 'pageSize' //每页数据量的参数名，默认：limit
      },
      where: {
        // area: area,
        rangeTime: rangeTime,
        titleOrContent: $(".searchone").val(),
        platformUid: $("#platformUid").val(),
        submitTargetIds:$("#submitTargetIds").val(),
		govOpen:$("#govOpen").val()
      },
      page: {
        curr: 1 //重新从第 1 页开始
      }
    });
  });
})

function timestampToDate(timestamp) {
  // var date = new Date(timestamp * 1000); // 将时间戳（秒）转换为毫秒，因为JavaScript的Date构造函数接受的是毫秒级时间戳 13位时间戳不需要
  var date = new Date(timestamp)
  var year = date.getFullYear();
  var month = ("0" + (date.getMonth() + 1)).slice(-2); // 月份从0开始，所以要加1，并且格式化为两位数字
  var day = ("0" + date.getDate()).slice(-2);

  return year + '-' + month + '-' + day;
}
