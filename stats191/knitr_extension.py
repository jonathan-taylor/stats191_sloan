import tempfile, sys, json, os
from shutil import rmtree
from glob import glob

from IPython.extensions import rmagic
from IPython.core.magic import cell_magic, Magics, register_cell_magic
from IPython.core.displaypub import publish_display_data
from IPython.core.magic_arguments import (
    argument, magic_arguments, parse_argstring
)

Rcode = """
library(knitr)
library(stringr)

ke = environment(knit)
render_ipynb = function (strict = FALSE) 
{
    knit_hooks$restore()
    opts_chunk$set(dev = "png", highlight = FALSE)
    hook.t = function(x, options) {
        fn = tempfile()
        of = file(fn, "w")
        writeChar(ke$indent_block(x), of)
        close(of)
        return(str_c('["text/plain","', fn, '"],'))
    }
    hook.o = function(x, options) {
        return(hook.t(x, options))
    }
    knit_hooks$set(source = hook.t, output = hook.o, warning = hook.t, error = hook.t, 
        message = hook.t, inline = function(x) sprintf(if (inherits(x, 
            "AsIs")) 
            "%s"
        else "`%s`", ke$.inline.hook(ke$format_sci(x, "html"))), plot = hook_plot_ipynb)
}

hook_plot_ipynb = function (x, options) 
{
    base = opts_knit$get("base.url")
    if(is.null(base)) {
        base = ''
    }
    filename = sprintf("%s%s", base, ke$.upload.url(x));
    return(sprintf('["image/png","%s"],', filename))
}

render_ipynb()
"""

rm = rmagic.RMagics(get_ipython())

def Reval(line):
    '''
    Parse and evaluate a line with rpy2.
    Returns the output to R's stdout() connection
    and the value of eval(parse(line)).
    '''
    #value = rmagic.ri.baseenv['eval'](rmagic.ri.parse(line))
    #value
    try: 
        return rm.notknitr_eval(line)
    except:
        return rm.eval(line)

Reval(Rcode)

@register_cell_magic
# @skip_doctest
# @magic_arguments()
# @argument(
#     None, '--noeval', 
#     help='Evaluate Names of input variable from shell.user_ns to be assigned to R variables of the same names after calling self.pyconverter. Multiple names can be passed separated only by commas with no whitespace.'
#     default=False,
#     action='store_true'
#     )
# @argument(
#     None, '--nowarning', action='store_true',
#     help='Suppress warnings.',
#     default=False
#     )
# @argument(
#     None, '--noerror', action='store_true',
#     help='Suppress errors.',
#     default=False
#     )
# @argument(
#     None, '--nomessage', action='store_true',
#     help='Suppress messages.',
#     default=False
#     )
# @argument(
#     None, '--dpi', type=int,
#     help='dpi passed to knit as an argument',
#     )
# @argument(
#     None, '--caption', 
#     help='Figure caption.'
#     )
# @argument(
#     None, '--prompt', 
#     help='Show prompt.',
#     default=False,
#     action='store_true'
#     )
# @cell_magic
def knitr(line, cell=None):

    # args = parse_argstring(knitr, line)

    tmpd = tempfile.mkdtemp()
    tmpd = "/Users/jonathantaylor/Desktop/debug"

    Rmd_file = open("%s/code.Rmd" % tmpd, "w")
    md_filename = Rmd_file.name.replace("Rmd", "md")
    Rmd_file.write("""

``` {r fig.path="%s"}
%s
```

""" % (tmpd, cell.strip()))
    Rmd_file.close()
    Reval("library(knitr); knit('%s','%s')" % (Rmd_file.name, md_filename))
    sys.stdout.flush(); sys.stderr.flush()
    json_str = '[' + open(md_filename, 'r').read().strip()[:-1].replace('\n','\\n') + ']'
    md_output = json.loads(json_str)

    #sys.stderr.write(open(md_filename).read() + '\n')

    #sys.stderr.write(json_str)

    display_data = []
    # flush text streams before sending figures, helps a little with output
    for mime, fname in md_output:
        # synchronization in the console (though it's a bandaid, not a real sln)
        sys.stdout.flush(); sys.stderr.flush()
        data = open(fname).read()
        os.remove(fname)
        if data:
            display_data.append(('RMagic.R', {mime: data}))

    # kill the temporary directory
    # rmtree(tmpd)

    for tag, disp_d in display_data:
        publish_display_data(tag, disp_d)

if __name__ == "__main__":
    ip = get_ipython()
    ip.run_cell_magic("knitr", None, """X=rnorm(40)
    Y=rnorm(40)
    X
    plot(X,Y)""")
