#include <iostream>
#include <vector>

using namespace std;

static const long long MOD = 1000000007LL;

using Matrix = vector<vector<long long>>;

Matrix multiply_matrix(const Matrix& a, const Matrix& b) {
    int n = (int)a.size();
    int m = (int)b[0].size();
    int z = (int)b.size();
    Matrix res(n, vector<long long>(m, 0));

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            long long cur = 0;
            for (int k = 0; k < z; k++) {
                cur = (cur + a[i][k] * b[k][j]) % MOD;
            }
            res[i][j] = cur;
        }
    }

    return res;
}

Matrix identity_matrix(int n) {
    Matrix res(n, vector<long long>(n, 0));
    for (int i = 0; i < n; i++) {
        res[i][i] = 1;
    }
    return res;
}

Matrix power_matrix(Matrix a, long long p) {
    Matrix res = identity_matrix((int)a.size());
    while (p > 0) {
        if (p & 1LL) {
            res = multiply_matrix(res, a);
        }
        a = multiply_matrix(a, a);
        p >>= 1LL;
    }
    return res;
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

Matrix build_bad_transition(const vector<long long>& coeffs) {
    int k = (int)coeffs.size();
    int size = k + 2;
    Matrix t(size, vector<long long>(size, 0));

    // Намеренно неверно: коэффициенты перевернуты
    for (int j = 0; j < k; j++) {
        t[0][j] = coeffs[k - 1 - j] % MOD;
    }

    for (int i = 1; i < k; i++) {
        t[i][i - 1] = 1;
    }

    // Намеренно неверно: суммы почти не обновляются
    t[k][k] = 1;
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
        for (int i = 0; i < (int)n; i++) s = (s + initial[i]) % MOD;
        long long w = s; // намеренно неверно
        cout << fn << ' ' << s << ' ' << w << '\n';
        return 0;
    }

    vector<long long> state(k + 2, 0);

    // Намеренно неверный порядок
    for (int i = 0; i < k; i++) {
        state[i] = initial[i];
    }

    long long sum_init = 0;
    for (long long x : initial) {
        sum_init = (sum_init + x) % MOD;
    }

    state[k] = sum_init;
    state[k + 1] = sum_init;

    Matrix t = build_bad_transition(coeffs);
    Matrix pw = power_matrix(t, n - k);
    vector<long long> ans = multiply_matrix_vector(pw, state);

    long long fn = ans[0];
    long long s = ans[k];
    long long w = ans[k + 1]; // намеренно неверно

    cout << fn << ' ' << s << ' ' << w << '\n';
    return 0;
}
