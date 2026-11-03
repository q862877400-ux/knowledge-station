$('.subTabTitle li').click(function(){
  var _this = $(this)
  var ind = _this.index()
  if(!_this.hasClass('on')){
      _this.addClass('on').siblings('li').removeClass('on')
      _this.parents('.subTab').find('.subTabBox .subTabBoxItem').eq(ind).addClass('subTabActive')
      .siblings('.subTabBoxItem').removeClass('subTabActive')
  }
})