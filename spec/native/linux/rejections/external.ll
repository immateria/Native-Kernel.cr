declare i64 @write(i32, ptr, i64)
define i32 @main() {
  %result = call i64 @write(i32 1, ptr null, i64 0)
  ret i32 0
}
