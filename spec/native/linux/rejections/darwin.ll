define i32 @main() {
  %result = call i64 asm sideeffect "mov x16, $3\0Asvc #0x80\0Acset $2, cs", "={x0},={x1},=r,r,{x0},{x1},{x2},{x3},{x4},{x5},{x6},{x7},~{x16},~{memory},~{cc}"()
  ret i32 0
}
