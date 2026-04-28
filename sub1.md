MOD = 1000000007


def add_mod(a, b):
    return (a + b) % MOD


def sub_mod(a, b):
    return (a - b) % MOD


def mul_mod(a, b):
    return (a * b) % MOD


def build_prefix(values):
    pref = []
    s = 0
    for x in values:
        s = add_mod(s, x)
        pref.append(s)
    return pref


def matrix_mul(a, b):
    n = len(a)
    m = len(b[0])
    inner = len(b)
    result = [[0] * m for _ in range(n)]

    for i in range(n):
        for k in range(inner):
            if a[i][k] == 0:
                continue
            aik = a[i][k]
            for j in range(m):
                if b[k][j] == 0:
                    continue
                result[i][j] = (result[i][j] + aik * b[k][j]) % MOD

    return result


def matrix_pow(base, power):
    size = len(base)
    result = [[0] * size for _ in range(size)]
    for i in range(size):
        result[i][i] = 1

    current = [row[:] for row in base]

    while power > 0:
        if power & 1:
            result = matrix_mul(result, current)
        current = matrix_mul(current, current)
        power >>= 1

    return result


def matrix_vec_mul(mat, vec):
    n = len(mat)
    result = [0] * n
    for i in range(n):
        total = 0
        for j in range(len(vec)):
            total += mat[i][j] * vec[j]
        result[i] = total % MOD
    return result


def build_transition(coeffs):
    k = len(coeffs)
    size = k + 2
    t = [[0] * size for _ in range(size)]

    for j in range(k):
        t[0][j] = coeffs[j] % MOD

    for i in range(1, k):
        t[i][i - 1] = 1

    for j in range(k):
        t[k][j] = coeffs[j] % MOD
    t[k][k] = 1

    for j in range(k):
        t[k + 1][j] = coeffs[j] % MOD
    t[k + 1][k] = 1
    t[k + 1][k + 1] = 1

    return t


def solve_small(n, initial):
    fn = initial[n - 1] % MOD
    s = sum(initial[:n]) % MOD
    w = 0
    for i in range(n):
        w = (w + (i + 1) * initial[i]) % MOD
    return fn, s, w


def main():
    k, n = map(int, input().split())
    coeffs = list(map(int, input().split()))
    initial = list(map(int, input().split()))

    coeffs = [x % MOD for x in coeffs]
    initial = [x % MOD for x in initial]

    if n <= k:
        fn, s, w = solve_small(n, initial)
        print(fn, s, w)
        return

    prefix = build_prefix(initial)
    prefix_sum = sum(prefix) % MOD

    state = [0] * (k + 2)

    # Немного неидеально оформлено, но корректно:
    # храним [F_k, F_{k-1}, ..., F_1, S_k, Q_k]
    for i in range(k):
        state[i] = initial[k - 1 - i]

    state[k] = prefix[-1]
    state[k + 1] = prefix_sum

    transition = build_transition(coeffs)
    power = n - k
    powered = matrix_pow(transition, power)
    final_state = matrix_vec_mul(powered, state)

    fn = final_state[0]
    s = final_state[k]
    q = final_state[k + 1]

    w = ((n + 1) % MOD) * s % MOD
    w = sub_mod(w, q)

    print(fn, s, w)


if __name__ == "__main__":
    main()
