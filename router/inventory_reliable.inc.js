function loadInventory(attempt){
  return inventoryCall().then(function(data){
    if(!data||typeof data!=='object'||!Array.isArray(data.profiles)||!Array.isArray(data.servers)||!data.settings||typeof data.settings.enabled!=='boolean')throw new Error('RPC-INVENTORY-INVALID');
    return data;
  }).catch(function(){
    if(attempt<2)return new Promise(function(resolve){setTimeout(resolve,250*(attempt+1));}).then(function(){return loadInventory(attempt+1);});
    return {profiles:[],servers:[],settings:{},error:'RPC-INVENTORY-UNAVAILABLE'};
  });
}
