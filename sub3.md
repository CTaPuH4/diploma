#include <iostream>
#include <vector>

using namespace std;

static const long long MOD = 1000000007LL;

long long add_mod(long long a, long long b) {
    a %= MOD;
    b %= MOD;
    long long r = a + b;
    if (r >= MOD) r -= MOD;
    return r;
}

long long sub_mod(long long a, long long b) {
    a %= MOD;
    b %= MOD;
    long long r = a - b;
    if (r < 0) r += MOD;
    return r;
}

long long mul_mod(long long a, long long b) {
    return (a % MOD) * (b % MOD) % MOD;
}

using Matrix = vector<vector<long long>>;

Matrix make_identity(int n) {
    Matrix id(n, vector<long long>(n, 0));
    for (int i = 0; i < n; i++) {
        id[i][i] = 1;
    }
    return id;
}

Matrix multiply_matrix(const Matrix& a, const Matrix& b) {
    int n = (int)a.size();
    int m = (int)b[0].size();
    int inner = (int)b.size();
    Matrix res(n, vector<long long>(m, 0));

    for (int i = 0; i < n; i++) {
        for (int k = 0; k < inner; k++) {
            if (a[i][k] == 0) continue;
            long long aik = a[i][k];
            for (int j = 0; j < m; j++) {
                if (b[k][j] == 0) continue;
                res[i][j] = (res[i][j] + aik * b[k][j]) % MOD;
            }
        }
    }

    return res;
}

Matrix power_matrix(Matrix base, long long power) {
    int n = (int)base.size();
    Matrix result = make_identity(n);

    while (power > 0) {
        if (power & 1LL) {
            result = multiply_matrix(result, base);
        }
        base = multiply_matrix(base, base);
        power >>= 1LL;
    }

    return result;
}

vector<long long> multiply_matrix_vector(const Matrix& a, const vector<long long>& v) {
    int n = (int)a.size();
    vector<long long> res(n, 0);

    for (int i = 0; i < n; i++) {
        long long total = 0;
        for (int j = 0; j < (int)v.size(); j++) {
            total = (total + a[i][j] * v[j]) % MOD;
        }
        res[i] = total;
    }

    return res;
}

vector<long long> build_prefix(const vector<long long>& initial) {
    vector<long long> pref;
    pref.reserve(initial.size());
    long long s = 0;
    for (long long x : initial) {
        s = add_mod(s, x);
        pref.push_back(s);
    }
    return pref;
}

Matrix build_transition(const vector<long long>& coeffs) {
    int k = (int)coeffs.size();
    int size = k + 2;
    Matrix t(size, vector<long long>(size, 0));

    for (int j = 0; j < k; j++) {
        t[0][j] = coeffs[j] % MOD;
    }

    for (int i = 1; i < k; i++) {
        t[i][i - 1] = 1;
    }

    for (int j = 0; j < k; j++) {
        t[k][j] = coeffs[j] % MOD;
    }
    t[k][k] = 1;

    for (int j = 0; j < k; j++) {
        t[k + 1][j] = coeffs[j] % MOD;
    }
    t[k + 1][k] = 1;
    t[k + 1][k + 1] = 1;

    return t;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int k;
    long long n;
    cin >> k >> n;

    vector<long long> coeffs(k), initial(k);
    for (int i = 0; i < k; i++) cin >> coeffs[i];
    for (int i = 0; i < k; i++) cin >> initial[i];

    for (int i = 0; i < k; i++) {
        coeffs[i] %= MOD;
        initial[i] %= MOD;
    }

    if (n <= k) {
        long long fn = initial[(int)n - 1] % MOD;
        long long s = 0;
        long long w = 0;

        for (int i = 0; i < (int)n; i++) {
            s = add_mod(s, initial[i]);
            w = (w + (long long)(i + 1) * initial[i]) % MOD;
        }

        cout << fn << ' ' << s << ' ' << w << '\n';
        return 0;
    }

    vector<long long> pref = build_prefix(initial);
    long long qk = 0;
    for (long long x : pref) {
        qk = add_mod(qk, x);
    }

    vector<long long> state(k + 2, 0);

    // Не самый изящный стиль, но корректно:
    // [F_k, F_{k-1}, ..., F_1, S_k, Q_k]
    for (int i = 0; i < k; i++) {
        state[i] = initial[k - 1 - i];
    }

    state[k] = pref.back();
    state[k + 1] = qk;

    Matrix transition = build_transition(coeffs);
    Matrix powered = power_matrix(transition, n - k);
    vector<long long> ans = multiply_matrix_vector(powered, state);

    long long fn = ans[0];
    long long s = ans[k];
    long long q = ans[k + 1];
    long long w = sub_mod(((n + 1) % MOD) * s % MOD, q);

    cout << fn << ' ' << s << ' ' << w << '\n';
    return 0;
}
