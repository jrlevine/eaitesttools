%rebase('eaibase.tpl', name=name)
<p>&nbsp;</p><p>&nbsp;</p><p>&nbsp;</p><p>&nbsp;</p>
<center>
%if defined('kvetch'):
    <p><font color="red">{{!kvetch}}</font></p>
%end
    <p>Logged in as {{user}}</p>
</center>
