/* Test-only producer-shaped website metric; never part of the shipped page. */
const urls={google:'https://www.google.com/generate_204',cloudflare:'https://www.cloudflare.com/cdn-cgi/trace',wikipedia:'https://www.wikipedia.org/'};
const METRIC='websites-https-mean-ms-v1',TARGET_SET='google-cloudflare-wikipedia-v1';
function website(profile,avg=20,time=profile.time){
 const protocol=profile.protocol||(String(profile.id).startsWith('openvpn:')?'openvpn':'wireguard'),iface=profile.interface||(protocol==='wireguard'?'wgclient1':'ovpnclient1'),generation=profile.vendor_generation||'a'.repeat(32);
 return {...profile,protocol,interface:iface,vendor_state:profile.vendor_state||'SETTLED',vendor_generation:generation,vendor_tunnel_id:profile.vendor_tunnel_id||protocol+':'+iface,website_response:{metric:METRIC,target_set:TARGET_SET,state:'ok',avg_ms:avg,time,valid_for:45,successes:3,attempted:3,interface:iface,vendor_tunnel_id:profile.vendor_tunnel_id||protocol+':'+iface,generation,results:Object.keys(urls).map(id=>({id,url:urls[id],state:'ok',elapsed_ms:avg,code:null}))}};
}
function history(pair,rows){return {version:1,metric:METRIC,target_set:TARGET_SET,row_encoding:'sum-tenths',pair,rows:rows.map(r=>[r[0],r[3]?Math.round(r[1]*r[3]*10):null,r[4]?Math.round(r[2]*r[4]*10):null,r[3],r[4],r[5]])};}
module.exports={website,history,METRIC,TARGET_SET};
