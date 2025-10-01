import React from 'react';

const Spinner = () => (
  <div className="text-center my-8 animate-fade-in">
    <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-emerald-500 border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]"></div>
    <p className="mt-4 text-lg font-semibold text-slate-700">Đang phân tích...</p>
    <p className="text-slate-500">Hệ thống đang xử lý hình ảnh và dữ liệu thời tiết. Vui lòng chờ trong giây lát.</p>
  </div>
);

export default Spinner;