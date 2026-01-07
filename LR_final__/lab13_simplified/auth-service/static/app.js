(async function(){
  try{
    const r = await fetch('/ui-config');
    if(!r.ok) return;
    const cfg = await r.json();
    document.getElementById('welcome')?.textContent = cfg.WELCOME_MESSAGE || document.getElementById('welcome')?.textContent;
    document.getElementById('login-title')?.textContent = cfg.LOGIN_TITLE || document.getElementById('login-title')?.textContent;
    document.getElementById('register-title')?.textContent = cfg.REGISTER_TITLE || document.getElementById('register-title')?.textContent;
  }catch(e){/* ignore */ }
})();
