/* Four common questions first. Existing full help and topic handlers are retained. */
function renderMinimumHelp(existingHelp,inventory){
  var full=E('details',{'class':'hv-minimum-details','data-minimum-disclosure':'all-help'},[
    E('summary',{},bi('All instructions and codes','Все инструкции и коды')),existingHelp
  ].filter(Boolean));
  if(typeof rememberDisclosure==='function')rememberDisclosure(full,'minimum-all-help');
  var topics=[
    ['no-internet','No internet','Нет интернета','Check the working channel and recovery steps.','Проверить рабочий канал и восстановление.'],
    ['auto-refuses','Start and stop','Запуск и остановка','Understand Auto commands and a refused start.','Разобраться с командами Auto и отказом запуска.'],
    ['reserve','Primary and reserve','Основной и резервный','Understand channel selection and switching.','Понять выбор канала и переключение.'],
    ['setup-guide','Setup','Настройка','Review the pair and required setup steps.','Проверить пару и обязательные шаги настройки.']
  ];
  var links=topics.map(function(topic){
    return E('button',{'type':'button','class':'hv-minimum-help-topic','data-minimum-help-topic':topic[0],'click':function(){
      full.open=true;
      if(typeof openHelpTopic==='function')openHelpTopic(topic[0]);
    }},[E('strong',{},bi(topic[1],topic[2])),E('span',{},bi(topic[3],topic[4]))]);
  });
  return E('section',{'class':'hv-minimum-section hv-minimum-help'},[
    renderAutoSchematic(inventory),E('div',{'class':'hv-minimum-help-grid'},links),full
  ]);
}
