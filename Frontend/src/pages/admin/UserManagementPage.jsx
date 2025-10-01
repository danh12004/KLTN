import React, { useState, useEffect, useCallback } from 'react';
import api from '../../api';
import Spinner from '../../components/Spinner';
import { UserPlus, Edit, Trash2, X } from 'lucide-react';
import toast from 'react-hot-toast';

const UserManagementPage = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  const [showForm, setShowForm] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', password: '', full_name: '', role: 'farmer' });

  const [editUser, setEditUser] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/admin/users');
      setUsers(response.data);
    } catch (error) {
      console.error("Lỗi khi lấy danh sách người dùng:", error);
      toast.error("Không tải được danh sách người dùng");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleAddUser = async () => {
    try {
      const response = await api.post('/admin/users', newUser);
      setUsers(prev => [...prev, response.data]);
      setShowForm(false);
      setNewUser({ username: '', password: '', full_name: '', role: 'farmer' });
      toast.success("Thêm người dùng thành công!");
    } catch (error) {
      console.error(error);
      toast.error("Thêm người dùng thất bại!");
    }
  };

  const handleUpdateUser = async () => {
    try {
      await api.put(`/admin/users/${editUser.id}`, editUser);
      setUsers(prev => prev.map(u => u.id === editUser.id ? editUser : u));
      setEditUser(null);
      toast.success("Cập nhật người dùng thành công!");
    } catch (error) {
      console.error(error);
      toast.error("Cập nhật người dùng thất bại!");
    }
  };

  const handleDeleteUser = async (userId) => {
    try {
      await api.delete(`/admin/users/${userId}`);
      setUsers(prev => prev.filter(u => u.id !== userId));
      setConfirmDelete(null);
      toast.success("Xóa người dùng thành công!");
    } catch (error) {
      console.error(error);
      toast.error("Xóa người dùng thất bại!");
    }
  };

  if (loading) return <Spinner />;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-slate-800">Quản lý Người dùng</h1>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 bg-blue-600 text-white font-semibold py-2 px-4 rounded-lg hover:bg-blue-700 cursor-pointer"
        >
          <UserPlus size={18} /> Thêm Người dùng
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-md border border-slate-200 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b border-slate-200 text-sm text-slate-600">
            <tr>
              <th className="p-4">ID</th>
              <th className="p-4">Tên đăng nhập</th>
              <th className="p-4">Họ và Tên</th>
              <th className="p-4">Vai trò</th>
              <th className="p-4">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.id} className="border-b border-slate-200 hover:bg-slate-50">
                <td className="p-4">{user.id}</td>
                <td className="p-4 font-medium">{user.username}</td>
                <td className="p-4">{user.full_name || 'Chưa cập nhật'}</td>
                <td className="p-4">
                  <span className={`text-xs font-semibold px-2 py-1 rounded-full ${user.role === 'admin'
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'bg-emerald-100 text-emerald-700'
                    }`}>
                    {user.role}
                  </span>
                </td>
                <td className="p-4 flex gap-2">
                  <button
                    onClick={() => setEditUser(user)}
                    className="text-blue-600 hover:text-blue-800 cursor-pointer"
                    title="Chỉnh sửa"
                  >
                    <Edit size={18} />
                  </button>
                  <button
                    onClick={() => setConfirmDelete(user)}
                    className="text-red-600 hover:text-red-800 cursor-pointer"
                    title="Xóa"
                  >
                    <Trash2 size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Form thêm user */}
      {showForm && (
        <div className="fixed inset-0 bg-white/70 backdrop-blur-sm flex justify-center items-center">
          <div className="bg-white p-6 rounded-lg w-96 shadow-lg relative">
            <button onClick={() => setShowForm(false)} className="absolute top-3 right-3 text-slate-500 hover:text-slate-800 cursor-pointer">
              <X size={20} />
            </button>
            <h2 className="text-lg font-bold mb-4">Thêm Người dùng</h2>
            <input type="text" placeholder="Tên đăng nhập" value={newUser.username}
              onChange={e => setNewUser({ ...newUser, username: e.target.value })}
              className="w-full border rounded p-2 mb-2" />
            <input type="password" placeholder="Mật khẩu" value={newUser.password}
              onChange={e => setNewUser({ ...newUser, password: e.target.value })}
              className="w-full border rounded p-2 mb-2" />
            <input type="text" placeholder="Họ và Tên" value={newUser.full_name}
              onChange={e => setNewUser({ ...newUser, full_name: e.target.value })}
              className="w-full border rounded p-2 mb-2" />
            <select value={newUser.role}
              onChange={e => setNewUser({ ...newUser, role: e.target.value })}
              className="w-full border rounded p-2 mb-4">
              <option value="farmer">Farmer</option>
              <option value="admin">Admin</option>
            </select>
            <button onClick={handleAddUser} className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 cursor-pointer">
              Thêm
            </button>
          </div>
        </div>
      )}

      {/* Form chỉnh sửa user */}
      {editUser && (
        <div className="fixed inset-0 bg-white/70 backdrop-blur-sm flex justify-center items-center">
          <div className="bg-white p-6 rounded-lg w-96 shadow-lg relative">
            <button onClick={() => setEditUser(null)} className="absolute top-3 right-3 text-slate-500 hover:text-slate-800 cursor-pointer">
              <X size={20} />
            </button>
            <h2 className="text-lg font-bold mb-4">Chỉnh sửa Người dùng</h2>
            <input type="text" value={editUser.full_name}
              onChange={e => setEditUser({ ...editUser, full_name: e.target.value })}
              className="w-full border rounded p-2 mb-2" />
            <select value={editUser.role}
              onChange={e => setEditUser({ ...editUser, role: e.target.value })}
              className="w-full border rounded p-2 mb-4">
              <option value="farmer">Farmer</option>
              <option value="admin">Admin</option>
            </select>
            <input type="password" placeholder="Để trống nếu không đổi mật khẩu"
              onChange={e => setEditUser({ ...editUser, password: e.target.value })}
              className="w-full border rounded p-2 mb-2" />
            <button onClick={handleUpdateUser} className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 cursor-pointer">
              Cập nhật
            </button>
          </div>
        </div>
      )}

      {/* Xác nhận xóa */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-white/70 backdrop-blur-sm flex justify-center items-center">
          <div className="bg-white p-6 rounded-lg w-80 shadow-lg">
            <h2 className="text-lg font-bold mb-4 text-red-600">Xác nhận xóa</h2>
            <p>Bạn có chắc chắn muốn xóa user <strong>{confirmDelete.username}</strong>?</p>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setConfirmDelete(null)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 cursor-pointer">
                Hủy
              </button>
              <button onClick={() => handleDeleteUser(confirmDelete.id)} className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 cursor-pointer">
                Xóa
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagementPage;
