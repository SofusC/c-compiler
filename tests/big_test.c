int add(int a, int b) {
    return a + b;
}

int sub(int a, int b) {
    return a - b;
}

int mul(int a, int b) {
    int result = 0;
    int i = 0;
    while (i < b) {
        result = result + a;
        i = i + 1;
    }
    return result;
}

int div(int a, int b) {
    int result = 0;
    int sum = b;
    while (sum <= a) {
        result = result + 1;
        sum = sum + b;
    }
    return result;
}

int mod(int a, int b) {
    int d = div(a, b);
    return a - mul(d, b);
}

int pow(int base, int exp) {
    int result = 1;
    int i = 0;
    while (i < exp) {
        result = mul(result, base);
        i = i + 1;
    }
    return result;
}

int factorial(int n) {
    if (n == 0) {
        return 1;
    }
    return mul(n, factorial(sub(n, 1)));
}

int fibonacci(int n) {
    if (n == 0) return 0;
    if (n == 1) return 1;
    return add(fibonacci(sub(n, 1)), fibonacci(sub(n, 2)));
}

int is_prime(int n) {
    if (n <= 1) return 0;
    int i = 2;
    while (i < n) {
        if (mod(n, i) == 0) return 0;
        i = i + 1;
    }
    return 1;
}

int gcd(int a, int b) {
    while (b != 0) {
        int t = b;
        b = mod(a, b);
        a = t;
    }
    return a;
}

int lcm(int a, int b) {
    return div(mul(a, b), gcd(a, b));
}

// A "print" stub (emits return value only)
int print_int(int x) {
    return x;
}

int test_arithmetic(void) {
    int a = 15;
    int b = 6;
    int s = add(a, b);
    int d = sub(a, b);
    int p = mul(a, b);
    int q = div(a, b);
    int r = mod(a, b);
    int po = pow(a, 2);

    print_int(s);
    print_int(d);
    print_int(p);
    print_int(q);
    print_int(r);
    print_int(po);

    return 0;
}

int test_factorial(void) {
    int i = 0;
    while (i <= 6) {
        int f = factorial(i);
        print_int(f);
        i = i + 1;
    }
    return 0;
}

int test_fibonacci(void) {
    int i = 0;
    while (i <= 10) {
        int f = fibonacci(i);
        print_int(f);
        i = i + 1;
    }
    return 0;
}

int test_primes(void) {
    int i = 1;
    while (i <= 20) {
        int p = is_prime(i);
        if (p == 1) {
            print_int(i);
        }
        i = i + 1;
    }
    return 0;
}

int test_gcd_lcm(void) {
    int a = 20;
    int b = 12;
    int g = gcd(a, b);
    int l = lcm(a, b);
    print_int(g);
    print_int(l);
    return 0;
}

int test_nested_operations(void) {
    int x = 5;
    int y = 3;
    int z = add(mul(x, x), mul(y, y)); // x² + y²
    print_int(z);

    int w = pow(add(x, y), 2); // (x + y)^2
    print_int(w);

    return 0;
}

int main(void) {
    test_arithmetic();
    test_factorial();
    test_fibonacci();
    test_primes();
    test_gcd_lcm();
    test_nested_operations();
    return 0;
}

