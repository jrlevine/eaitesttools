%rebase('eaibase.tpl', name=name)
{{!boilerplate}}
<center>
%if defined('kvetch') and kvetch:
    <p><font color="red">{{!kvetch}}</font></p>
%end
</center>

<blockquote>
<p><em>Name:</em> {{prod['name']}}</p>
<p><em>Vendor:</em> {{prod['vendor']}}</p>
<p><em>Email:</em> {{prod['email']}}</p>
<p><em>Features:</em> {{prod['types']}}</p>
</blockquote>
