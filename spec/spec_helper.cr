require "spec"
require "../src/native-kernel/source"
require "../src/native-kernel/audit"
{% if flag?(:darwin) %}
  require "../src/native-kernel"
{% end %}
