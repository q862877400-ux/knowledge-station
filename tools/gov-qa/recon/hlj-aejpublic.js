// aes Encrypt
var _keyVal = '';
function Encrypt(val) {
  getKey(val);
  // 直接返回
  return  _keyVal;
}

function getKeyVal(data) {
  var key = ''
  var newkey = Object.keys(data).sort();
  var newObj = {}
  var timestamp = getDateTime()
  // 参数按字母排序
  for (var i = 0; i < newkey.length; i++) {
    newObj[newkey[i]] = data[newkey[i]]
  }
  // 转json
  for (var k in newObj) {
    if (typeof newObj[k] == 'object') {
      key += k + JSON.stringify(newObj[k])
    } else {
      key += k + newObj[k]
    }
  }
  // 时间戳 + json参数
  console.log(   )
  return {"sign": Encrypt(timestamp + "" + key), "timestamp": timestamp}
}

function getDateTime() {
  var date = new Date
  return date.getTime()
}
//获取key
function getKey(obj) {
  $.ajax({
    url: '/communication/api-base/dict/getKey',
    type: 'post',
    data: {
      'val': obj
    },
    async: false,
    success: function(res){
      if(res.status == 'success'){
        _keyVal = res.data
      }
    },
    error: function(err){
      console.log(err)
    }
  })
}