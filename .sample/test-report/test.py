import argparse

# cong 3 so thuc
# a: float/int, default = 10
# b: float/int, default = 20
# c: float/int, default = 30
# return tong 3 so
def add_three_numbers(a=10, b=20, c=30):
    """Hàm tính tổng 3 số a, b, c với giá trị mặc định là 10, 20, 30"""
    return a + b + c

# bootstrap app
if __name__ == "__main__":
    # Khởi tạo parser cho các tham số dòng lệnh
    parser = argparse.ArgumentParser(description="Tính tổng 3 số từ CLI với tham số tường minh --a, --b, --c")

    # Định nghĩa các tham số --a, --b, --c với giá trị mặc định
    parser.add_argument("--a", type=float, default=10, help="Số thứ nhất (mặc định: 10)")
    parser.add_argument("--b", type=float, default=20, help="Số thứ hai (mặc định: 20)")
    parser.add_argument("--c", type=float, default=30, help="Số thứ ba (mặc định: 30)")

    args = parser.parse_args()

    # Làm tròn int nếu là số nguyên tròn để in ra đẹp hơn
    a = int(args.a) if args.a.is_integer() else args.a
    b = int(args.b) if args.b.is_integer() else args.b
    c = int(args.c) if args.c.is_integer() else args.c

    result = add_three_numbers(a, b, c)

    print(f"Tham so nhan duoc: a={a}, b={b}, c={c}")
    print(f"Tong 3 so la: {result}")
    print("Het chuong trinh")