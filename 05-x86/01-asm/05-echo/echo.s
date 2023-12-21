main:
        push    %rbx

loop:
        push    %rdi                    # save registers that puts uses
        push    %rsi
        sub     $8, %rsp                # must align stack before call

        mov     (%rsi), %rdi            # the argument string to display
        call    puts                    # print it

        add     $8, %rsp                # restore %rsp to pre-aligned value
        pop     %rsi                    # restore registers puts used
        pop     %rdi

        add     $8, %rsi                # point to next argument
        dec     %rdi                    # count down
        jnz     loop                    # if not done counting keep going

        pop     %rbx
        ret
