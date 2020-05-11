#include <stdio.h>
#include <stdlib.h>

int main() {
    FILE *fp = fopen("test.txt", "w");
    for (int i = 0; i < 10; i++) {
        printf("%d\n", i);
        for (int j = 0; j < 10000000; j++) {
            fprintf(fp, "hello");
        }
    }
    fclose(fp);
}
