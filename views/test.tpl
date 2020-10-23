%rebase('eaibase.tpl', name=name)
{{!boilerplate}}
<center>
%if defined('kvetch') and kvetch:
    <p><font color="red">{{!kvetch}}</font></p>
%end
</center>

<p>| <a href="/test/{{tid-1}}">Previous</a> | <a href="/test/{{tid+1}}">Next</a> | </p>

<p><em>Type:</em> {{test['testtype']}}</p>
<p><em>Summary:</em> {{test['summary']}}</p>
<p><em>Description:</em> {{test['description']}}</p>
<p><em>Action:</em> {{test['action']}}</p>
<p><em>Expected:</em> {{test['expected']}}</p>
<p><em>Class:</em> {{test['class']}}</p>
