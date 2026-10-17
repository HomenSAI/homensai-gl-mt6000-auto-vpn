/* Server labels: protocol and country instead of host names or addresses. The country is read from the profile name the
   VPN provider gave (for example de1459.nordvpn.com or "Germany Berlin"); it is never looked up from an IP address. */
var COUNTRIES={
  al:['Albania','Албания'],ar:['Argentina','Аргентина'],am:['Armenia','Армения'],au:['Australia','Австралия'],at:['Austria','Австрия'],az:['Azerbaijan','Азербайджан'],
  bd:['Bangladesh','Бангладеш'],be:['Belgium','Бельгия'],ba:['Bosnia and Herzegovina','Босния и Герцеговина'],br:['Brazil','Бразилия'],bg:['Bulgaria','Болгария'],
  by:['Belarus','Беларусь'],ca:['Canada','Канада'],ch:['Switzerland','Швейцария'],cl:['Chile','Чили'],co:['Colombia','Колумбия'],cr:['Costa Rica','Коста-Рика'],
  hr:['Croatia','Хорватия'],cy:['Cyprus','Кипр'],cz:['Czechia','Чехия'],dk:['Denmark','Дания'],de:['Germany','Германия'],ee:['Estonia','Эстония'],es:['Spain','Испания'],
  fi:['Finland','Финляндия'],fr:['France','Франция'],gb:['United Kingdom','Великобритания'],ge:['Georgia','Грузия'],gr:['Greece','Греция'],hk:['Hong Kong','Гонконг'],
  hu:['Hungary','Венгрия'],is:['Iceland','Исландия'],in:['India','Индия'],id:['Indonesia','Индонезия'],ie:['Ireland','Ирландия'],il:['Israel','Израиль'],it:['Italy','Италия'],
  jp:['Japan','Япония'],kz:['Kazakhstan','Казахстан'],kr:['South Korea','Южная Корея'],lv:['Latvia','Латвия'],lt:['Lithuania','Литва'],lu:['Luxembourg','Люксембург'],
  md:['Moldova','Молдова'],me:['Montenegro','Черногория'],mk:['North Macedonia','Северная Македония'],mx:['Mexico','Мексика'],my:['Malaysia','Малайзия'],nl:['Netherlands','Нидерланды'],
  nz:['New Zealand','Новая Зеландия'],no:['Norway','Норвегия'],pa:['Panama','Панама'],pe:['Peru','Перу'],ph:['Philippines','Филиппины'],pl:['Poland','Польша'],pt:['Portugal','Португалия'],
  ro:['Romania','Румыния'],rs:['Serbia','Сербия'],ru:['Russia','Россия'],sg:['Singapore','Сингапур'],sk:['Slovakia','Словакия'],si:['Slovenia','Словения'],za:['South Africa','Южная Африка'],
  se:['Sweden','Швеция'],th:['Thailand','Таиланд'],tr:['Turkey','Турция'],tw:['Taiwan','Тайвань'],ua:['Ukraine','Украина'],ae:['United Arab Emirates','ОАЭ'],us:['United States','США'],
  uy:['Uruguay','Уругвай'],uz:['Uzbekistan','Узбекистан'],vn:['Vietnam','Вьетнам']
};
var COUNTRY_ALIASES={uk:'gb',usa:'us',uae:'ae',holland:'nl','czech republic':'cz','south korea':'kr',korea:'kr'};
function countryCodeFromName(text){
  if(typeof text!=='string'||!text)return null;
  var name=text.toLowerCase().slice(0,96),code;
  // 1. A country written out (English or Russian), longest name first so "south africa" never reads as "africa".
  var words=[];Object.keys(COUNTRIES).forEach(function(key){words.push([COUNTRIES[key][0].toLowerCase(),key]);words.push([COUNTRIES[key][1].toLowerCase(),key]);});
  Object.keys(COUNTRY_ALIASES).forEach(function(alias){words.push([alias,COUNTRY_ALIASES[alias]]);});
  words.sort(function(a,b){return b[0].length-a[0].length;});
  for(var i=0;i<words.length;i++){
    var at=name.indexOf(words[i][0]);
    if(at>=0&&words[i][0].length>=3&&!/[a-zа-я]/.test(name.charAt(at-1)||' ')&&!/[a-zа-я]/.test(name.charAt(at+words[i][0].length)||' '))return words[i][1];
  }
  // 2. Provider host names and short names: de1459.nordvpn.com, ua68.nordvpn.com.udp, de-fra-001, us_ny_2, "DE Berlin".
  var match=/^([a-z]{2})(?:[0-9]{1,5}(?=[._-]|$)|[-_ ])/.exec(name)||/^([a-z]{2})$/.exec(name);
  if(match){code=COUNTRY_ALIASES[match[1]]||match[1];if(COUNTRIES[code])return code;}
  return null;
}
function countryOf(profile){
  if(!profile)return null;
  var code=countryCodeFromName(profile.router_name)||countryCodeFromName(profile.name)||countryCodeFromName(profile.channel);
  return code?{code:code,en:COUNTRIES[code][0],ru:COUNTRIES[code][1]}:null;
}
function countryName(profile){var country=countryOf(profile);return country?bi(country.en,country.ru):'';}
function countryLabel(profile){return bi('Country: ','Страна: ')+(countryName(profile)||bi('unknown','не определена'));}
function protocolLabel(profile){return profile&&profile.protocol==='wireguard'?'WireGuard':'OpenVPN';}
// A name the owner chose; the provider's host name is never repeated on screen.
function customName(profile){return profile&&profile.router_name&&profile.name&&profile.name!==profile.router_name?String(profile.name):'';}
function serverTitle(profile){
  var country=countryName(profile);
  return country?country+' · '+protocolLabel(profile)+(customName(profile)?' · '+customName(profile):''):(customName(profile)||(profile&&profile.name)||'—');
}
