@counter = global i32 0
define i32 @main() {
  store i32 1, ptr @counter
  ret i32 0
}
