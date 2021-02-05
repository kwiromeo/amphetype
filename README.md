
# Amphetype: Resurrected

Amphetype is an advanced typing practice program.

Features include:

* Type your favorite novel!

  One of the core ideas behind Amphetype was to not just use boring
  "stock texts" for typing practice, but to allow me to type texts I
  actually want to read as well. So one feature is the ability to
  import whole novels (for example from [Project
  Gutenberg](https://www.gutenberg.org/)) and have Amphetype
  automatically generate bite-sized lessons from the text. (When I was
  learning the [Colemak](https://colemak.com/) keyboard layout, I
  typed _The Metamorphosis_ by Franz Kafka!)
  
* Typing statistics.

  It provides the basic typing statistics (accuracy and WPM), as well
  as identifying the keys/trigrams/words that break your flow and what
  impact these "viscous" combinations have on your typing speed
  overall. Together with graphs over time and so forth.
  
* Generate lessons from past statistics.

  Amphetype features an advanced lesson generator where you can
  generate texts based on your past performance. Generate blocks of
  text to target practice your slowest words, trigrams, or keys!

* Layout-agnostic.

  Amphetype doesn't care _what_ keyboard or layout you use, it only
  looks at _how_ you use it. As such it's likely not suitable for
  complete typing beginners who need an on-screen keyboard.

* Highly customizable with regard to look and feel.

# Installing

I could use some help in generating installers for MacOS and Windows.

But for now the easiest and recommended way to install is to make sure
your system has Python (version 3.6+ required) installed and then
install via `pip` or `pip3`:

``` bash
$ pip install amphetype
```

This should give you an executable command `amphetype`, so simply run
it:

``` bash
$ amphetype
```

# Resurrected?

Yes, I originally made this program 12 years ago
[here](https://code.google.com/archive/p/amphetype/). I've updated it
somewhat, included some features that were requested back then, and
upgraded the code to use Python 3 and Qt5 (instead of Python 2 and
Qt4).

# Other Links

Review of (old) Amphetype: https://forum.colemak.com/topic/2201-training-with-amphetype/

My own inspiration for switching to a different keyboard layout and why I made Amphetype:

* http://steve-yegge.blogspot.com/2008/09/programmings-dirtiest-little-secret.html

* https://blog.codinghorror.com/we-are-typists-first-programmers-second/

* https://www.ryanheise.com/colemak/

# Screenshots

**TODO**.

Using various themes:

![screenshot1](screenshot-typer.png)
![screenshot2](screenshot-pref.png)
![screenshot3](screenshot-graph.png)
![screenshot4](screenshot5.png)
