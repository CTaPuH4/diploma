MOD = 1000000007


def mat_mul(a, b):
    n = len(a)
    m = len(b[0])
    z = len(b)
    res = [[0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            cur = 0
            for k in range(z):
                cur += a[i][k] * b[k][j]
            res[i][j] = cur % MOD
    return res


def mat_pow(a, p):
    n = len(a)
    res = [[0] * n for _ in range(n)]
    for i in range(n):
        res[i][i] = 1
    while p > 0:
        if p & 1:
            res = mat_mul(res, a)
        a = mat_mul(a, a)
        p >>= 1
    return res


def mat_vec(a, v):
    n = len(a)
    res = [0] * n
    for i in range(n):
        total = 0
        for j in range(len(v)):
            total += a[i][j] * v[j]
        res[i] = total % MOD
    return res


def build_bad_transition(coeffs):
    k = len(coeffs)
    size = k + 2
    t = [[0] * size for _ in range(size)]

    # Намеренно неправильная логика:
    # коэффициенты ставятся в обратном порядке
    for j in range(k):
        t[0][j] = coeffs[k - 1 - j] % MOD

    for i in range(1, k):
        t[i][i - 1] = 1

    # Намеренно неверное накопление сумм
    t[k][k] = 1
    t[k + 1][k + 1] = 1
    return t


def main():
    k, n = map(int, input().split())
    coeffs = list(map(int, input().split()))
    initial = list(map(int, input().split()))

    coeffs = [x % MOD for x in coeffs]
    initial = [x % MOD for x in initial]

    if n <= k:
        fn = initial[n - 1] % MOD
        s = sum(initial[:n]) % MOD
        w = sum(initial[:n]) % MOD  # намеренно неверно
        print(fn, s, w)
        return

    state = [0] * (k + 2)

    # Тоже намеренно неверно: кладем не в том порядке
    for i in range(k):
        state[i] = initial[i]

    state[k] = sum(initial) % MOD
    state[k + 1] = sum(initial) % MOD

    t = build_bad_transition(coeffs)
    pw = mat_pow(t, n - k)
    ans = mat_vec(pw, state)

    fn = ans[0]
    s = ans[k]
    w = ans[k + 1]  # намеренно неверно

    print(fn, s, w)


if __name__ == "__main__":
    main()
