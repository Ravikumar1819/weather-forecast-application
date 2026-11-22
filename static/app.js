const $=id=>document.getElementById(id);
let generation=0;
$('search').onsubmit=async e=>{
 e.preventDefault();const mine=++generation;$('search-button').disabled=true;$('search-button').textContent='Checking…';$('message').hidden=true;$('weather').hidden=true;
 try{
  const response=await fetch('/api/weather?'+new URLSearchParams({city:$('city').value,units:$('units').value}));const r=await response.json();if(!response.ok)throw new Error(r.error||'Weather unavailable.');if(mine!==generation)return;
  const symbol=r.units==='metric'?'°C':'°F',speed=r.units==='metric'?'m/s':'mph';
  $('location').textContent=r.city+', '+r.country;$('temperature').textContent=Math.round(r.current.temperature)+symbol;$('conditions').textContent=r.current.description;
  $('feels').textContent=Math.round(r.current.feels_like)+symbol;$('humidity').textContent=r.current.humidity+'%';$('wind').textContent=r.current.wind_speed+' '+speed;
  $('mode').hidden=!r.demo;$('mode').textContent='Demo mode: generated sample values, not live weather for this location.';
  $('updated').textContent='Retrieved '+new Date(r.updated_at).toLocaleString()+'. '+(r.demo?'Sample data.':'Weather data provided by OpenWeather.');
  $('forecast').replaceChildren();for(const day of r.forecast){const a=document.createElement('article');const d=new Date((day.time+r.timezone)*1000);for(const [tag,value] of [['h3',d.toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric',timeZone:'UTC'})],['strong',Math.round(day.temperature)+symbol],['p',day.description]]){const node=document.createElement(tag);node.textContent=value;a.append(node);}$('forecast').append(a);}
  if(!r.forecast.length)$('forecast').textContent='No upcoming forecast readings available.';$('weather').hidden=false;
 }catch(error){$('message').textContent=error.message;$('message').className='notice error';$('message').hidden=false;}
 finally{if(mine===generation){$('search-button').disabled=false;$('search-button').textContent='Check weather';}}
};
